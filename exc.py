from typing import Generic, NamedTuple, TypeVar


class Error(Exception):
    """Base class for other exceptions"""

    def __init__(self, msg: str, src_error: Exception | None = None):
        super().__init__(msg)
        self.msg = msg
        self.src_error = src_error

    def __str__(self):
        return f'{self.msg} ({self.src_error})'


T = TypeVar('T')


class Result(NamedTuple, Generic[T]):
    """
    A type that represents either a value or an error, similar to Go's multiple return values.

    Usage example:
    ```python
    def divide(x: int, y: int) -> Result[int | None]:
        try:
            return Result(value=x / y, error=None)
        except ZeroDivisionError as e:
            return Result(value=None, error=Error(msg='Division by zero error', src_error=e))
    ```
    """

    value: T
    error: Error | None
