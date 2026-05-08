import json
import typing
import uuid
from collections.abc import Iterable, Callable

from util.default import DEFAULT
from util.path_util import PREFERRED_FILENAME_LIMIT, sanitize_filename
from util.safe_execute import OneshotExecutor
from youtube.core import run_yt_dlp, YTDLPOptions


class __DumpPlayListExtractor(OneshotExecutor):
    @staticmethod
    def __info_get(info, key: str, message: str) -> typing.Any:
        value = info.get(key, DEFAULT)
        if value is DEFAULT:
            print(message)
        return value

    @classmethod
    def __extract_url_recursive(cls, info) -> Iterable[str]:
        url_type = info.get('_type', 'video')
        if url_type in ('playlist', 'multi_video', 'compat_list'):  # noqa
            for video_dict in info.get('entries', []):
                yield from cls.__extract_url_recursive(video_dict)
        elif url_type == 'url':
            yield info['url']
        elif url_type == 'video':
            yield info['webpage_url']
        else:
            raise ValueError(f'Invalid url type {url_type}')

    def __init__(self, url: str, callback: Callable[[Iterable[str], str], None]):
        super().__init__()
        self._url = url
        self._callback = callback

    def _execute(self):
        options = YTDLPOptions.default().copy_with(
            '--flat-playlist',
            '--dump-single-json',
            self._url
        )
        info = json.loads(run_yt_dlp(options, capture_stdout=True).stdout)
        title = self.__info_get(
            info, 'title', 'Playlist title is unavailable, use ID instead')
        title = title or self.__info_get(
            info, 'id', 'Playlist ID is unavailable, use random UUID instead')
        title = title or uuid.uuid4().hex
        # Sanitize playlist title
        self._callback(
            self.__extract_url_recursive(info),
            sanitize_filename(title)[0:PREFERRED_FILENAME_LIMIT]
        )


def dump_playlist(url: str, callback: Callable[[Iterable[str], str], None]):
    __DumpPlayListExtractor(url, callback).execute()
