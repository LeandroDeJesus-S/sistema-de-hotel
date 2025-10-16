from typing import Callable, Generic, TypeVar


class Error(Exception):
    """Base class for other exceptions"""

    def __init__(self, msg: str, src_error: Exception | None = None):
        super().__init__(msg)
        self.msg = msg
        self.src_error = src_error

    def __str__(self):
        return f'{self.msg} ({self.src_error})'


T = TypeVar('T')
U = TypeVar('U')


class Result(Generic[T]):
    """
    Represents the outcome of an operation that can either succeed (Ok) or fail (Err).

    This monadic structure allows safe chaining of operations without exceptions
    or nested conditionals, similar to Rust's `Result` or Haskell's `Either`.
    """

    def __init__(self, ok: bool, value: T | Error):
        """
        Initialize a new Result instance.

        Args:
            ok: Indicates whether the result is success (`True`) or error (`False`).
            value: The contained success value (`T`) or error value (`Error`).
        """
        self._ok = ok
        self._value = value

    @staticmethod
    def Ok(value: T) -> 'Result[T]':
        """
        Create a success result.

        Args:
            value: Value to store on success.

        Returns:
            Result: A `Result` object representing success.
        """
        return Result(True, value)

    @staticmethod
    def Err(msg: str, src_error: Exception | None = None) -> 'Result[T]':
        """
        Create an error result.

        Args:
            msg: The error message.
            src_error: The source error.

        Returns:
            Result: A `Result` object representing error.
        """
        return Result(False, Error(msg, src_error))

    def is_ok(self) -> bool:
        """
        Check if the result is a success.

        Returns:
            bool: `True` if success, `False` otherwise.
        """
        return self._ok

    def is_err(self) -> bool:
        """
        Check if the result is an error.

        Returns:
            bool: `True` if error, `False` otherwise.
        """
        return not self._ok

    def unwrap(self) -> T:
        """
        Unwrap the success value or raise an exception if it's an error.

        Returns:
            T: The contained success value.

        Raises:
            Exception: If called on an `Err` result.
        """
        if self._ok:
            return self._value  # type: ignore
        raise Exception(f'Unwrap called on Err: {self._value}')

    def unwrap_or(self, default: T) -> T:
        """
        Return the success value or a default if it's an error.

        Args:
            default: Default value to return if the result is an error.

        Returns:
            T: The success value or the default value.
        """
        return self._value if self._ok else default  # type: ignore

    def map(self, fn: Callable[[T], U]) -> 'Result[U]':
        """
        Apply a function to the success value, if present.

        Args:
            fn: Function to apply to the success value (`T -> U`).

        Returns:
            Result[U]: New `Result` with the transformed value if `Ok`,
            or the same error if `Err`.
        """
        if self._ok:
            return Result.Ok(fn(self._value))  # type: ignore
        return Result.Err(self._value.msg, self._value.src_error)  # type: ignore

    def map_err(self, fn: Callable[[Error], U]) -> 'Result[T]':
        """
        Apply a function to the error value, if present.

        Args:
            fn: Function to apply to the error (`Error -> U`).

        Returns:
            Result[T]: New `Result` with the transformed error if `Err`,
            or the same success value if `Ok`.
        """
        if self._ok:
            return Result.Ok(self._value)  # type: ignore
        return Result.Err(fn(self._value))  # type: ignore

    def unwrap_err(self) -> Error:
        """
        Unwrap the error value or raise an exception if it's a success.

        Returns:
            Error: The contained error value.

        Raises:
            Exception: If called on an `Ok` result.
        """
        if not self._ok:
            return self._value  # type: ignore
        raise Exception(f'Unwrap_err called on Ok: {self._value}')

    def then(self, fn: Callable[[T], 'Result[U]']) -> 'Result[U]':
        """
        Chain another operation that also returns a `Result`.

        If the current result is `Ok`, apply `fn(value)`.
        If it's `Err`, propagate the error and skip `fn`.

        Args:
            fn: Function that receives the success value and returns another `Result`.

        Returns:
            Result[U]: The next operation's result or the propagated error.
        """
        if self._ok:
            return fn(self._value)  # type: ignore
        return Result.Err(self._value.msg, self._value.src_error)  # type: ignore

    def match(self, on_ok: Callable[[T], U], on_err: Callable[[Error], U]) -> U:
        """
        Execute one of two functions depending on the result type.

        Args:
            on_ok: Function executed if the result is `Ok`.
            on_err: Function executed if the result is `Err`.

        Returns:
            U: The return value of the corresponding function.
        """
        return on_ok(self._value) if self._ok else on_err(self._value)  # type: ignore

    def __repr__(self) -> str:
        """
        Return a human-readable string representation of the result.

        Returns:
            str: `Ok(value)` or `Err(value)` representation.
        """
        return f'Ok({self._value})' if self._ok else f'Err({self._value})'
