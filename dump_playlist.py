import typing

from util.input_util import URLOption, BooleanOption, URLKind
from util.path_util import ROOT_PATH
from util.safe_execute import OneshotExecutor
from youtube.playlist import dump_playlist


class MainExecutor(OneshotExecutor):
    @staticmethod
    def __callback(urls: typing.Iterable[str], title: str):
        stem = f'{title}.txt'
        url_list = ROOT_PATH / stem
        if url_list.exists():
            overwrite = BooleanOption.show(f'File "{stem}" already exists, overwrite?')
        else:
            overwrite = True
        if overwrite:
            with open(url_list, 'w', encoding='utf-8') as f:
                iterator = iter(urls)
                try:
                    f.write(next(iterator))
                    for line in iterator:
                        f.write(f'\n{line}')
                except StopIteration:
                    pass
            print(f'URL list saved to "{url_list}"')
        else:
            print(f'URL list "{url_list}" skipped')

    def _execute(self):
        url = URLOption.show(URLKind.PlayList, False)
        dump_playlist(url, self.__callback)


MainExecutor().execute()
