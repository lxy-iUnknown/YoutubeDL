import os
import pathlib
import shutil
import typing

import pathvalidate
from pathvalidate.handler import NullValueHandler

from util.safe_execute import Verbosity, SafeExecutor

ROOT_PATH = pathlib.Path.cwd()


def __preferred_filename_limit():
    default_filename_limit = 255
    filename_limit = default_filename_limit
    if os.name == 'nt':
        import ctypes.wintypes

        from util.external import Kernel32

        # Windows still doesn't support create long directory even if LongPathsEnabled is set
        # For example: os.mkdir('a' * 1000)
        limit = ctypes.wintypes.DWORD()
        result = Kernel32.GetVolumeInformationW(
            f'{ROOT_PATH.drive}\\',
            None, 0, None,
            ctypes.byref(limit),
            None, None, 0
        )
        if result:
            filename_limit = limit.value
    else:
        try:
            filename_limit = os.pathconf(ROOT_PATH, 'PC_PATH_MAX')
        except (ValueError, OSError):
            pass
    return min(filename_limit, default_filename_limit) // 2


PREFERRED_FILENAME_LIMIT = __preferred_filename_limit()


class __RemoveDirectoryExecutor(SafeExecutor[None]):
    def __init__(self, path: os.PathLike[typing.AnyStr] | typing.AnyStr,
                 recursive: bool = False):
        super().__init__(Verbosity.FirstEntry, loop=False)
        self._path = path
        self._recursive = recursive

    @staticmethod
    def __function_full_name(function) -> str:
        name = function.__name__
        try:
            module = function.__module__
            if module in {'nt', 'posix'}:
                module = 'os'
            return f'{module}.{name}'
        except AttributeError:
            return name

    @classmethod
    def __format_note(cls, item: tuple[typing.Any, str, BaseException]) -> str:
        function, path, exc = item
        if isinstance(exc, OSError):
            message = exc.strerror
        else:
            message = str(exc)
        return f'Error calling {cls.__function_full_name(function)}("{path}"): {message}'

    def _execute(self):
        if self._recursive:
            def handle_error(function, path, exc):
                errors.append((function, path, exc))

            errors = []
            shutil.rmtree(self._path, onexc=handle_error)
            if errors:
                e = Exception('shutil.rmtree failed')
                e.__notes__ = list(map(self.__format_note, errors))
                raise e
        else:
            os.rmdir(self._path)


def sanitize_filename(name: str) -> str:
    return pathvalidate.sanitize_filename(
        name,
        null_value_handler=NullValueHandler.return_timestamp,
    )


def remove_directory(path: os.PathLike[typing.AnyStr] | typing.AnyStr,
                     recursive: bool = False):
    __RemoveDirectoryExecutor(path, recursive).execute()
