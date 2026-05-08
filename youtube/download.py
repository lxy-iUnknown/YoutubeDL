import abc
import base64
import hashlib
import os
import pathlib
import subprocess
import threading
import time
import typing
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, CancelledError

from util.default import DEFAULT
from util.input_util import BooleanOption, IntOption, StrOption
from util.path_util import ROOT_PATH, remove_directory
from util.safe_execute import Verbosity, SafeExecutor
from youtube.core import YTDLPOptions, run_yt_dlp


def __ensure_deps_named(name):
    try:
        subprocess.run(
            name,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        raise ValueError(f'{name} is unavailable or broken') from e


def __ensure_deps():
    __ensure_deps_named('yt-dlp')
    __ensure_deps_named('ffmpeg')


def __default_concurrency():
    class __Holder[T]:
        def __init__(self, value: T):
            self.value: T = value

    lock = threading.Lock()
    done = __Holder(False)
    max_workers = __Holder(0)

    def initializer():
        with lock:
            max_workers.value += 1

    def blocking_worker():
        while not done.value:
            time.sleep(0.0001)

    with ThreadPoolExecutor(initializer=initializer) as executor:
        while True:
            prev_max_workers = max_workers.value
            executor.submit(blocking_worker)
            if max_workers.value == prev_max_workers:
                done.value = True
                return prev_max_workers


__ensure_deps()
__DEFAULT_CONCURRENCY = __default_concurrency()
__DOWNLOAD_OPTIONS = YTDLPOptions(
    # Fixed by https://github.com/yt-dlp/yt-dlp/pull/8328
    '--extractor-retries', 'infinite',
    '--fragment-retries', 'infinite',
    '--windows-filenames' if os.name == 'nt' else '--no-windows-filenames',
)

__SUBTITLE_SLEEP_INTERVAL = 30

__DOWNLOAD_AUDIO = BooleanOption('Download audio')
__DOWNLOAD_SUBTITLE = BooleanOption('Download subtitle')
__SUBTITLE_LANGUAGE = StrOption("Subtitle language (e.g. en.*,ja)")
# https://github.com/yt-dlp/yt-dlp/issues/13831
__SUBTITLE_SLEEP = BooleanOption(f'Subtitle sleep ({__SUBTITLE_SLEEP_INTERVAL}s)')
__FILES_OPTION = IntOption(
    'Number of concurrent files', 0, description='0: auto')
__MAXIMUM_RESOLUTION = IntOption(
    'Maximum resolution', 0, description='0: best')

__FETCHED_COUNT = 2

DOWNLOAD_BASE_PATH = ROOT_PATH / 'download'
TEMP_BASE_PATH = ROOT_PATH / 'temp'


class __DownloadOneArgs(typing.NamedTuple):
    options: YTDLPOptions
    url: str
    home_path_root: pathlib.Path
    temp_path_root: pathlib.Path


class __URLSet:
    def __init__(self, iterable: Iterable[str]):
        self._fetched: set[str] = set()
        self._rest = iter(iterable)

    def _fetch_one(self) -> str:
        fetched = self._fetched
        while True:
            value = next(self._rest)
            if value not in fetched:
                fetched.add(value)
                return value

    def fetch(self, count: int = 1):
        if count < 0:
            raise ValueError(f'Count({count}) < 0')
        result = 0
        for i in range(count):
            if not self.fetch_one():
                break
            result += 1
        return result

    def fetch_one(self):
        try:
            return self._fetch_one()
        except StopIteration:
            return DEFAULT

    def __iter__(self):
        yield from self._fetched
        while True:
            try:
                yield self._fetch_one()
            except StopIteration:
                self._fetched.clear()
                break


class __Executor(abc.ABC):
    @abc.abstractmethod
    def submit(self, func, *args, **kwargs):
        pass

    @abc.abstractmethod
    def __enter__(self):
        pass

    @abc.abstractmethod
    def __exit__(self, *args):
        pass


class __SequentialExecutor(__Executor):
    def submit(self, func, *args, **kwargs):
        func(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class __ThreadedExecutor(__Executor):
    __MAIN_TID = threading.main_thread().ident

    @staticmethod
    def __is_alive(future):
        # Future.cancelled, Future.done, Future.running are BLOCKING!!!
        try:
            future.result(0.001)
            return False
        except TimeoutError:
            return True
        except CancelledError:
            return True

    def __init__(self, concurrency: int):
        self._executor = ThreadPoolExecutor(concurrency)
        self._futures = []

    def submit(self, func, *args, **kwargs):
        future = self._executor.submit(func, *args, **kwargs)
        self._futures.append(future)

    def __enter__(self):
        self._executor.__enter__()
        return self

    def __exit__(self, *args):
        # Naive polling to make it interruptable
        while True:
            has_unfinished = False
            for future in self._futures:
                if self.__is_alive(future):
                    # Yield execution
                    has_unfinished = True
                    break
            if not has_unfinished:
                break


class __DownloadOneExecutor(SafeExecutor[None]):
    def __init__(self, args: __DownloadOneArgs):
        super().__init__(Verbosity.MessageOnly, True)
        url_hash = self.__hash_url(args.url)
        # Important: use separate temporary path for each file to prevent file contention
        temp_path = str(args.temp_path_root / url_hash)
        self._url = args.url
        self._temp_path = temp_path
        self._temp_path_root = args.temp_path_root
        self._options = args.options.copy_with(
            '--paths', f'home:{str(args.home_path_root)}',
            '--paths', f'temp:{str(temp_path)}'
        )

    @staticmethod
    def __hash_url(url: str):
        sha_hash = hashlib.sha1(url.encode('utf-8')).digest()
        # Replace +/ with -_
        base64_hash = base64.b64encode(sha_hash[:12], altchars=b'-_')
        return base64_hash.decode('utf-8')

    def _execute(self):
        print(f'Downloading URL "{self._url}"')
        run_yt_dlp(self._options.copy_with(self._url))
        print(f'Download URL "{self._url}" finished')

    def _cleanup(self):
        remove_directory(self._temp_path)
        remove_directory(self._temp_path_root)


def get_download_options():
    options = __DOWNLOAD_OPTIONS.copy()
    download_audio = __DOWNLOAD_AUDIO.result()
    options.append('--format', f'{'bv+ba/b' if download_audio else 'bv/b'}')
    maximum_resolution = __MAXIMUM_RESOLUTION.result()
    if maximum_resolution:
        options.append('--format-sort', f'res:{maximum_resolution}')
    download_subtitle = __DOWNLOAD_SUBTITLE.result()
    if download_subtitle:
        options.append('--write-subs', '--write-auto-subs')
        subtitle_language = __SUBTITLE_LANGUAGE.result()
        options.append('--sub-langs', subtitle_language)
        subtitle_sleep = __SUBTITLE_SLEEP.result()
        if subtitle_sleep:
            options.append('--sleep-subtitles', str(__SUBTITLE_SLEEP_INTERVAL))
    return options


def download(urls: Iterable[str], title: str):
    url_list = __URLSet(urls)
    if url_list.fetch_one() is DEFAULT:
        # No item
        return
    home_path_root = DOWNLOAD_BASE_PATH / title
    temp_path_root = TEMP_BASE_PATH / title
    options = get_download_options()
    if url_list.fetch_one():
        expected = __FILES_OPTION.result()
        if not expected:  # expected == 0
            expected = __DEFAULT_CONCURRENCY
        if expected >= __FETCHED_COUNT:
            concurrency = url_list.fetch(expected - __FETCHED_COUNT) + __FETCHED_COUNT
        else:
            concurrency = min(expected, __FETCHED_COUNT)
    else:
        # Has only one item
        concurrency = 1
    if concurrency == 1:
        executor = __SequentialExecutor()
    else:
        executor = __ThreadedExecutor(concurrency)
    with executor:
        for url in url_list:
            args = __DownloadOneArgs(options, url, home_path_root, temp_path_root)
            executor.submit(__DownloadOneExecutor(args).execute)
    remove_directory(TEMP_BASE_PATH)
