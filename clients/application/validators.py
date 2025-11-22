from typing import Protocol, TypeVar

from exc import Result

T = TypeVar('T', bound='AbsValidator')


class AbsValidator(Protocol[T]):
    raise_exc: bool

    def validate(self, value: T) -> Result[T]:
        """ "Validates the given value and returns a Result object containing
        the database-ready format or an Error object if validation fails.
        """
