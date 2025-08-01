import time
import functools

class RetryError(Exception):
    '''
    Exception to signal that a function should be retried
    '''
    pass

def retryable(*, retries=5, delay=1, fallback=None):
    """
    A decorator that retries a function upon RetryError.

    Args:
        retries (int): Number of retry attempts.
        delay (float): Delay between retries in seconds.
        fallback (Any): Value to return after all retries fail instead of raising.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except RetryError:
                    attempt += 1
                    if attempt < retries:
                        time.sleep(delay)
                    else:
                        if fallback is not None:
                            return fallback
                        raise
        return wrapper
    return decorator