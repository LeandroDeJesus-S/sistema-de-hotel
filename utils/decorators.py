from functools import wraps
from typing import Callable

from exc import Error, Result


def ensure_result(error_msg: str | Callable = ''):
    """Decorator that catches any exception in a use case and returns a Result object."""

    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            try:
                raw_result = func(*args, **kwargs)
                return (
                    Result.Ok(raw_result) if not isinstance(raw_result, Result) else raw_result
                )
            except Error as e:
                return Result.Err(e.msg, e.src_error)
            except Exception as e:
                return Result.Err(error_msg or str(e), e)

        return decorated

    return decorator if isinstance(error_msg, str) else decorator(error_msg)
