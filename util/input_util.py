import abc
import enum

from util.safe_execute import Verbosity, NoFailureExecutor


@enum.verify(enum.UNIQUE)
class URLKind(enum.IntEnum):
    Video = 1,
    PlayList = 2,
    VideoOrPlayList = 3


class Option[T](NoFailureExecutor[T]):
    class __Ignorable(Exception):
        pass

    def __init__(self, name: str, description: str | None = None):
        super().__init__(Verbosity.MessageOnly, True)
        self._name = name
        self._description = description
        self._prompt: str | None = None

    def _get_prompt(self):
        prompt = self._prompt
        if not prompt:
            if self._description:
                prompt = f'{self._name} ({self._description}): '
            else:
                prompt = f'{self._name}: '
            self._prompt = prompt
        return prompt

    @abc.abstractmethod
    def _convert(self, value: str) -> T:
        pass

    def _execute(self) -> T:
        value = input(self._get_prompt()).strip()
        if value:
            return self._convert(value)
        raise self.__Ignorable()

    def _handle_error(self, error: Exception) -> bool:
        return isinstance(error, self.__Ignorable)


class StrOption(Option[str]):
    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)

    def _convert(self, value: str) -> str:
        return value


class StrListOption(Option[str]):
    def __init__(self, name: str, values: tuple[str, ...]):
        super().__init__(name, '/'.join(values))
        self._values = set(values)

    def _convert(self, value: str):
        if value in self._values:
            return value
        raise ValueError(f'{self._name} should be {self._description}, not "{value}"')


class BooleanOption(Option[bool]):
    def __init__(self, name: str):
        super().__init__(name, 'Y/N')

    def _convert(self, value: str):
        if value in {'y', 'Y'}:
            return True
        if value in {'n', 'N'}:
            return False
        raise ValueError(f'{self._name} should be Y/N, not "{value}"')

    @staticmethod
    def show(name: str):
        return BooleanOption(name).result()


class URLOption(Option[str | None]):
    def __init__(self, kind: URLKind, allow_exit: bool):
        if kind == URLKind.Video:
            description = 'Video URL'
        elif kind == URLKind.PlayList:
            description = 'Playlist URL'
        else:
            description = 'Video/Playlist URL'
        if allow_exit:
            description += ' (Type q/Q to quit)'
        super().__init__(description)
        self._allow_exit = allow_exit

    def _convert(self, value: str):
        if self._allow_exit and value in 'qQ':
            return None
        else:
            return value

    @staticmethod
    def show(kind: URLKind, allow_exit: bool):
        return URLOption(kind, allow_exit).result()


class IntOption(Option[int]):
    def __init__(self, name: str,
                 min_value: int | None = None, max_value: int | None = None,
                 description: str | None = None):
        super().__init__(name, description)
        if min_value is None and max_value is None:
            def validate(_: int):
                return True

            self._validator = validate
            self._error_description = ''
        elif min_value is None:
            def validate(value: int):
                return value <= max_value

            self._validator = validate
            self._error_description = f'not in range (-∞, {max_value}]'
        elif max_value is None:
            def validate(value: int):
                return value >= min_value

            self._validator = validate
            self._error_description = f'not in range [{min_value}, +∞)'
        else:
            if min_value > max_value:
                raise ValueError(f'minimum({min_value}) > maximum({max_value})')
            elif min_value == max_value:
                def validate(value: int):
                    return value == min_value

                self._validator = validate
                self._error_description = f'not equal to {min_value}'
            else:
                def validate(value: int):
                    return min_value <= value <= max_value

                self._validator = validate
                self._error_description = f'not in range [{min_value}, {max_value}]'

    def _convert(self, value: str) -> int:
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError(f'{self._name} should be integer, not "{value}"')
        if self._validator(int_value):
            return int_value
        raise ValueError(f'{self._name} {value} {self._error_description}')
