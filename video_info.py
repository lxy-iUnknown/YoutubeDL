from util.input_util import URLOption, URLKind
from util.safe_execute import OneshotExecutor, SafeExecutor, Verbosity
from youtube.core import run_yt_dlp, YTDLPOptions


class VideoInfoExecutor(SafeExecutor[bool]):
    __URL_OPTION = URLOption(URLKind.Video, True)

    def __init__(self):
        super().__init__(Verbosity.DontShow, True)
        self._options = YTDLPOptions.default().copy_with('--list-formats')

    def _execute(self) -> bool:
        url = self.__URL_OPTION.result()
        if url is None:
            return False
        run_yt_dlp(self._options.copy_with(url))
        return True


class MainExecutor(OneshotExecutor):
    def _execute(self):
        executor = VideoInfoExecutor()
        while True:
            result = executor.execute()
            if result.ok and not result.result:
                break


MainExecutor().execute()
