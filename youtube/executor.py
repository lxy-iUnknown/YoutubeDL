import abc
import threading
import time
from concurrent.futures import ThreadPoolExecutor, CancelledError

from common.default import DEFAULT
from youtube.util import with_default


class Executor(abc.ABC):
    _DEFAULT = DEFAULT

    class __Holder[T]:
        def __init__(self, value: T):
            self.value: T = value

    @classmethod
    def __get_default_concurrency(cls):
        lock = threading.Lock()
        done = cls.__Holder(False)
        max_workers = cls.__Holder(0)

        def initializer():
            with lock:
                max_workers.value += 1

        def blocking_worker():
            while not done.value:
                time.sleep(0.0001)

        with ThreadPoolExecutor(initializer=initializer) as executor:
            while True:
                prev_max_workers = max_workers.value
                executor.submit(blocking_worker)
                if max_workers.value == prev_max_workers:
                    done.value = True
                    return prev_max_workers

    @classmethod
    def _factory(cls):
        pass

    @abc.abstractmethod
    def submit(self, func, *args, **kwargs):
        pass

    @abc.abstractmethod
    def __enter__(self):
        pass

    @abc.abstractmethod
    def __exit__(self, *args):
        pass

    @classmethod
    def default_concurrency(cls):
        return with_default(cls, cls.__get_default_concurrency)

    @staticmethod
    def create(concurrency: int) -> Executor:
        if concurrency == 1:
            return _SequentialExecutor()
        return _ThreadedExecutor(concurrency)


class _SequentialExecutor(Executor):
    def submit(self, func, *args, **kwargs):
        func(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _ThreadedExecutor(Executor):
    __MAIN_TID = threading.main_thread().ident

    @staticmethod
    def __is_alive(future):
        # Future.cancelled, Future.done, Future.running are BLOCKING!!!
        try:
            future.result(0.001)
            return False
        except TimeoutError:
            return True
        except CancelledError:
            return True

    def __init__(self, concurrency: int):
        self._executor = ThreadPoolExecutor(concurrency)
        self._futures = []

    def submit(self, func, *args, **kwargs):
        future = self._executor.submit(func, *args, **kwargs)
        self._futures.append(future)

    def __enter__(self):
        self._executor.__enter__()
        return self

    def __exit__(self, *args):
        # Naive polling to make it interruptable
        while True:
            has_unfinished = False
            for future in self._futures:
                if self.__is_alive(future):
                    # Yield execution
                    has_unfinished = True
                    break
            if not has_unfinished:
                break
