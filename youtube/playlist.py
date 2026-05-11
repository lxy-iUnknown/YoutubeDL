import re
import typing
from collections.abc import Callable

from common.default import DEFAULT
from common.path_util import PREFERRED_FILENAME_LIMIT
from common.safe_execute import OneshotExecutor
from youtube.core import run_yt_dlp, YTDLPOptions
from youtube.util import simple_hash


class __DumpPlayListExtractor(OneshotExecutor):
    __TITLE_RE = re.compile(r'title=([\s\S]*?)(?=\nurl=)')
    __URL_RE = re.compile(r"url=(.*)")

    @staticmethod
    def __info_get(info, key: str, message: str) -> typing.Any:
        value = info.get(key, DEFAULT)
        if value is DEFAULT:
            print(message)
        return value

    def __init__(self, url: str, callback: Callable[[list[str], str], None]):
        super().__init__()
        self._url = url
        self._callback = callback

    def _execute(self):
        options = YTDLPOptions.default().copy_with(
            '--print',
            f'title=%(title|{simple_hash(self._url)})S',
            '--print',
            'url=%(webpage_url)s',
            self._url
        )
        stdout = run_yt_dlp(options, capture_stdout=True)
        # noinspection PyUnresolvedReferences
        title = self.__TITLE_RE.search(stdout).group(1)
        urls = self.__URL_RE.findall(stdout)
        self._callback(
            urls,
            title[0:PREFERRED_FILENAME_LIMIT]
        )


def dump_playlist(url: str, callback: Callable[[list[str], str], None]):
    __DumpPlayListExtractor(url, callback).execute()
