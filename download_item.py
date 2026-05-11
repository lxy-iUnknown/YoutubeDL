from common.input_util import URLOption, URLKind
from common.safe_execute import OneshotExecutor
from youtube.download import download
from youtube.playlist import dump_playlist


class MainExecutor(OneshotExecutor):
    def _execute(self):
        url = URLOption.show(URLKind.VideoOrPlayList, False)
        dump_playlist(url, download)


MainExecutor().execute()
