import time
from functools import wraps
from typing import Callable, TypeVar, Any, cast
import logging 

logger = logging.getLogger("Utilities")

F = TypeVar("F", bound=Callable[..., Any])

def retryable(retries:int=5, delay:int=1) -> Callable[[F], F]:
    """
    A decorator that retries a function upon exception.

    Args:
        retries (int): Number of retry attempts.
        delay (float): Delay between retries in seconds.
        fallback (Any): Value to return after all retries fail instead of raising.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args:Any, **kwargs:Any) -> Any:
            total_attempts = retries + 1
            for attempt in range(total_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt < retries:
                        time.sleep(delay)
                    else:
                        raise
            raise ValueError("Ran out of retry attempts")
        return cast(F,wrapper)
    return decorator