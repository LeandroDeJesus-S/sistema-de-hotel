from typing import Generic, TypeVar

from exc import Result

T = TypeVar('T')
R = TypeVar('R')


class UseCase(Generic[T, R]):
    def __call__(self, dto: T) -> Result[R]:
        """Executes the use case.

        Args:
            dto: The data transfer object containing the use case input.

        Returns:
            A Result containing the use case output or an Error.
        """
        raise NotImplementedError
