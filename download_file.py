import contextlib
import pathlib

from common.input_util import Option
from common.path_util import ROOT_PATH
from common.safe_execute import OneshotExecutor
from youtube.download import download


class PathOption(Option[pathlib.Path]):
    def __init__(self):
        super().__init__('Download file')

    def _convert(self, value: str):
        with contextlib.chdir(ROOT_PATH):
            p = pathlib.Path(value.replace('"', '')).absolute()
        if p.exists():
            return p
        raise ValueError(f'{self._name} "{value}" does not exist')

    @staticmethod
    def show():
        return PathOption().result()


class MainExecutor(OneshotExecutor):
    def _execute(self):
        def is_valid_line(line: str):
            return len(line) != 0 and not line.startswith('#')

        download_file = PathOption.show()
        with open(download_file, 'r', encoding='utf-8') as f:
            urls = list(filter(is_valid_line, map(str.strip, f)))
            download(urls, download_file.stem)


MainExecutor().execute()
