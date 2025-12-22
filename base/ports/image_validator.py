from typing import Protocol

from exc import Result


class AbsImage(Protocol):
    width: int | float
    height: int | float
    size: int | float


class ImageValidator(Protocol):
    """Performs validation on an image"""

    def __call__(self, image: AbsImage) -> Result[bool]: ...
