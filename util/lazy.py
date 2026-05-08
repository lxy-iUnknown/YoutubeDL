import abc

from util.default import DEFAULT


class Lazy[T](abc.ABC):
    def __init__(self):
        self._value = DEFAULT

    @abc.abstractmethod
    def _factory(self) -> T:
        pass

    @property
    def value(self) -> T:
        value = self._value
        if value is DEFAULT:
            self._value = value = self._factory()
        return value
