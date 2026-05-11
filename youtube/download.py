import os
import subprocess
import typing

from common.input_util import BooleanOption, IntOption, StrOption
from common.path_util import ROOT_PATH, remove_directory
from common.safe_execute import Verbosity, SafeExecutor
from youtube.core import YTDLPOptions, run_yt_dlp
from youtube.executor import Executor
from youtube.util import simple_hash


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


__ensure_deps()

__SUBTITLE_SLEEP_INTERVAL = 30
__DOWNLOAD_AUDIO = BooleanOption('Download audio')
__DOWNLOAD_SUBTITLE = BooleanOption('Download subtitle')
__SUBTITLE_LANGUAGE = StrOption("Subtitle language (can be regex, e.g. en\\S+,ja)")
# https://github.com/yt-dlp/yt-dlp/issues/13831
__SUBTITLE_SLEEP = BooleanOption(f'Subtitle sleep ({__SUBTITLE_SLEEP_INTERVAL}s)')
__FILES_OPTION = IntOption(
    'Number of concurrent files', 0, description='0: auto')
__MAXIMUM_RESOLUTION = IntOption(
    'Maximum resolution', 0, description='0: best')

DOWNLOAD_BASE_PATH = ROOT_PATH / 'download'
TEMP_BASE_PATH = ROOT_PATH / 'temp'


class __DownloadOneArgs(typing.NamedTuple):
    options: YTDLPOptions
    url: str
    title: str


class __DownloadOneExecutor(SafeExecutor[None]):
    def __init__(self, args: __DownloadOneArgs):
        super().__init__(Verbosity.MessageOnly, True)
        home_path = DOWNLOAD_BASE_PATH / args.title
        # Use hash(url)
        temp_path = TEMP_BASE_PATH / simple_hash(args.url)
        self._url = args.url
        self._temp_path = temp_path
        self._options = args.options.copy_with(
            '--paths', f'home:{str(home_path)}',
            '--paths', f'temp:{str(temp_path)}'
        )

    def _execute(self):
        print(f'Downloading URL "{self._url}"')
        run_yt_dlp(self._options.copy_with(self._url))
        print(f'Download URL "{self._url}" finished')

    def _cleanup(self):
        remove_directory(self._temp_path)


def get_download_options():
    options = YTDLPOptions.default().copy_with(
        # Fixed by https://github.com/yt-dlp/yt-dlp/pull/8328
        '--extractor-retries', 'infinite',
        '--fragment-retries', 'infinite',
        '--windows-filenames' if os.name == 'nt' else '--no-windows-filenames',
        '--no-playlist',
    )
    download_audio = __DOWNLOAD_AUDIO.result()
    options.append('--format', f'{'bv+ba/b' if download_audio else 'bv/b'}')
    maximum_resolution = __MAXIMUM_RESOLUTION.result()
    if maximum_resolution:
        options.append('--format-sort', f'res:{maximum_resolution}')
    download_subtitle = __DOWNLOAD_SUBTITLE.result()
    if download_subtitle:
        subtitle_language = __SUBTITLE_LANGUAGE.result()
        options.append(
            '--write-subs',
            '--write-auto-subs',
            # See https://github.com/yt-dlp/yt-dlp/issues/1501
            '--sub-langs', subtitle_language
        )
        subtitle_sleep = __SUBTITLE_SLEEP.result()
        if subtitle_sleep:
            options.append('--sleep-subtitles', str(__SUBTITLE_SLEEP_INTERVAL))
    return options


def download(urls: list[str], title: str):
    url_count = len(urls)
    if not url_count:
        return
    options = get_download_options()
    executor = Executor.create(
        min(__FILES_OPTION.result() or Executor.default_concurrency(), url_count)
    )
    with executor:
        for url in urls:
            args = __DownloadOneArgs(options, url, title)
            executor.submit(__DownloadOneExecutor(args).execute)
    remove_directory(TEMP_BASE_PATH)
