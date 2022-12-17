import functools
import threading
from typing import Callable, Any


class Singleton(type):
    __instances = {}
    __lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            with cls.__lock:
                if cls not in cls.__instances:
                    cls.__instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instances[cls]


def synchronized(wrapped: Callable) -> Callable:
    __lock = threading.Lock()

    @functools.wraps(wrapped)
    def _wrap(*args, **kwargs) -> Any:
        with __lock:
            return wrapped(*args, **kwargs)

    return _wrap
