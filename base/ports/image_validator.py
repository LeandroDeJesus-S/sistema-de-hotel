from abc import abstractmethod
from typing import Protocol

from exc import Result


class AbsImage(Protocol):
    """Represents an image with its basic properties."""

    width: int | float
    height: int | float
    size: int | float


class ImageValidator(Protocol):
    """Performs validation on an image"""

    @abstractmethod
    def __call__(self, image: AbsImage) -> Result[bool]:
        """Validates the given image."""
        ...
