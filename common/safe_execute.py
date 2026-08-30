import abc
import enum
import sys
import traceback
from warnings import deprecated


class ExceptionHandleArgs:
    def __init__(self, loop: bool, verbosity: Verbosity):
        self.loop = loop
        self.verbosity = verbosity
        self.handled = False


@enum.verify(enum.UNIQUE)
class Verbosity(enum.IntEnum):
    DontShow = 0,
    MessageOnly = 1,
    FirstEntry = 2,
    Full = 3


class Result[T]:
    def __init__(self, result: T | None, ok: bool):
        self._result = result
        self._ok = ok

    def __repr__(self):
        if self._ok:
            return f'Result({self._result})'
        return 'Result(<failed>)'

    @property
    def ok(self):
        return self._ok

    @property
    def result(self) -> T:
        if not self._ok:
            raise ValueError('Failed result')
        return self._result


class SafeExecutor[T](abc.ABC):
    def __init__(self, verbosity: Verbosity, loop: bool):
        self._verbosity = verbosity
        self._loop = loop

    def _execute_impl(self):
        # Contract: No exception = OK, Has exception = Failed
        try:
            return Result[T](self._execute(), True)
        except Exception as e:
            args = ExceptionHandleArgs(self._loop, self._verbosity)
            if isinstance(e, EOFError):
                pass
            self._handle_exception(e, args)
            self._verbosity = args.verbosity
            self._loop = args.loop
            if args.handled:
                pass
            elif self._verbosity == Verbosity.MessageOnly:
                print(e)
            elif self._verbosity == Verbosity.FirstEntry:
                traceback.print_exception(e, limit=1)
            elif self._verbosity == Verbosity.Full:
                traceback.print_exception(e)
            return Result[T](None, False)

    def execute(self) -> Result[T]:
        try:
            while True:
                result = self._execute_impl()
                if result.ok or not self._loop:
                    break
            return result
        finally:
            # Finally will block Ctrl+C
            try:
                self._cleanup()
            except Exception as e:
                sys.stderr.write(f'Exception ignored in {type(self).__name__}._cleanup:\n')
                traceback.print_exception(e)

    # Abstract methods
    @abc.abstractmethod
    def _execute(self) -> T:
        pass

    # Virtual methods
    def _cleanup(self) -> None:
        pass

    def _handle_exception(self, error: Exception, args: ExceptionHandleArgs):
        pass


class OneshotExecutor(SafeExecutor[None]):
    def __init__(self):
        super().__init__(Verbosity.Full, False)

    @abc.abstractmethod
    def _execute(self) -> None:
        pass


class NoFailureExecutor[T](SafeExecutor[T]):
    @abc.abstractmethod
    def _execute(self) -> None:
        pass

    @deprecated("Use result() instead")
    def execute(self) -> Result[T]:
        raise NotImplementedError(f'Use {type(self).__name__}.result() instead')

    def result(self) -> T:
        return super().execute().result
