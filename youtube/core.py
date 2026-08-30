import subprocess
import typing

from common.default import DEFAULT
from common.input_util import StrListOption, IntOption, BooleanOption
from youtube.util import with_default


class YTDLPOptions:
    _DEFAULT = DEFAULT

    def __init__(self, *args: str):
        self._options = list(args)

    @classmethod
    def __get_default_options(cls):
        no_proxy = 'none'
        proxy_type_option = StrListOption(
            'Proxy type',
            ('http', 'socks', 'socks5', no_proxy),
            case_sensitive=False
        )
        proxy_port_option = IntOption('Proxy port', 1, (1 << 16) - 1)
        verbosity_option = BooleanOption('Verbose')
        options = YTDLPOptions(
            # Disable HTTP chunk size to prevent fragment download error
            '--http-chunk-size', '1M',
            '--no-playlist',
            '--retries', 'infinite',
            '--no-cache-dir',
            # --trim-filename is buggy, so use output template to control file name limit
            # See https://github.com/yt-dlp/yt-dlp/issues/2314
            # See https://github.com/yt-dlp/yt-dlp/issues/1837#issuecomment-1100854653
            '--output', f'%(title)S [%(id)S].%(ext)S'
        )
        proxy_type = proxy_type_option.result()
        if proxy_type != no_proxy:
            proxy_port = proxy_port_option.result()
            options.append('--proxy', f'{proxy_type}://localhost:{proxy_port}')
        if verbosity_option.result():
            options.append('--verbose')
        return options

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

    @classmethod
    def default(cls):
        return with_default(cls, cls.__get_default_options)


@typing.overload
def run_yt_dlp(options: YTDLPOptions, capture_stdout: typing.Literal[False] = False) -> None:
    ...


@typing.overload
def run_yt_dlp(options: YTDLPOptions, capture_stdout: typing.Literal[True] = True) -> str:
    ...


def run_yt_dlp(options: YTDLPOptions, capture_stdout: typing.Literal[True, False] = False):
    process = subprocess.run(
        ['yt-dlp', '--encoding', 'utf-8'] + options.raw,
        stdout=subprocess.PIPE if capture_stdout else None,
        check=True,
    )
    if capture_stdout:
        return process.stdout.decode('utf-8').strip()
    return None


print(f'YT-DLP version: {run_yt_dlp(YTDLPOptions('--version'), capture_stdout=True)}')
