import atexit
import os
import subprocess

from util.input_util import StrListOption, IntOption
from util.path_util import remove_directory, PREFERRED_FILENAME_LIMIT


class YTDLPResult:
    def __init__(self, process):
        self.__process = process

    @property
    def stdout(self):
        return self.__process.stdout

    @property
    def stdout_str(self):
        return self.__process.stdout.decode('utf-8').strip()


class YTDLPOptions:
    __DEFAULT = None

    def __init__(self, *args):
        self._options = list(args)

    def __copy_with(self, *new_options: str):
        options = YTDLPOptions()
        options.append(*self._options)
        options.append(*new_options)
        return options

    def append(self, *options: str):
        self._options += options

    def copy(self):
        options = YTDLPOptions()
        options._options = self._options.copy()
        return options

    def copy_with(self, *new_options: str):
        return self.__copy_with(*new_options)

    @property
    def raw(self):
        return self._options

    @staticmethod
    def __init_default_options():
        cache_root = os.path.normpath(os.path.expanduser('~/.cache'))

        def remove_cache():
            remove_directory(cache_root, True)

        atexit.register(remove_cache)

        no_proxy = 'none'
        proxy_type_option = StrListOption(
            'Proxy type',
            ('http', 'socks', 'socks5', no_proxy)
        )
        proxy_port_option = IntOption('Proxy port', 1, (1 << 16) - 1)
        options = YTDLPOptions(
            # Disable HTTP chunk size to prevent fragment download error
            # 'http_chunk_size': 10 * 1024 * 1024,  # 10MB
            '--no-playlist',
            '--retries', 'infinite',
            '--cache-dir', cache_root,
            # --trim-filename is buggy, so use output template to control file name limit
            # See https://github.com/yt-dlp/yt-dlp/issues/2314
            # See https://github.com/yt-dlp/yt-dlp/issues/1837#issuecomment-1100854653
            '--output', f'%(title).{PREFERRED_FILENAME_LIMIT}s [%(id)s].%(ext)s'
        )
        proxy_type = proxy_type_option.result()
        if proxy_type != no_proxy:
            proxy_port = proxy_port_option.result()
            options.append('--proxy', f'{proxy_type}://localhost:{proxy_port}')
        return options

    @classmethod
    def default(cls):
        default_options = cls.__DEFAULT
        if default_options is None:
            cls.__DEFAULT = default_options = cls.__init_default_options()
        return default_options


def __run_yt_dlp(*options: str, capture_stdout=False):
    process = subprocess.run(
        ('yt-dlp',) + options,
        stdout=subprocess.PIPE if capture_stdout else None,
        check=True,
    )
    return YTDLPResult(process)


def __print_yt_dlp_version():
    result = __run_yt_dlp('--version', capture_stdout=True)
    print(f'YT-DLP version: {result.stdout_str}')


__print_yt_dlp_version()


def run_yt_dlp(options: YTDLPOptions, capture_stdout=False):
    return __run_yt_dlp(*options.raw, capture_stdout=capture_stdout)
