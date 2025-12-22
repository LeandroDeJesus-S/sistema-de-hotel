from dataclasses import dataclass

from django.core.exceptions import ValidationError

from base.ports.image_validator import AbsImage, ImageValidator
from exc import Result


@dataclass(frozen=True, slots=True, kw_only=True)
class MaxDimensionsImageValidator(ImageValidator):
    """Validates that an image's dimensions do not exceed maximum allowed values."""

    max_width: int | float
    max_height: int | float
    raise_exception: bool = False
    exception_class: type[Exception] | None = None
    error_message: str | None = None

    def __call__(self, image: AbsImage) -> Result[bool]:
        if image.width > self.max_width or image.height > self.max_height:
            if self.error_message:
                error_msg = self.error_message.format(
                    width=image.width,
                    height=image.height,
                    max_width=self.max_width,
                    max_height=self.max_height,
                )
            else:
                error_msg = (
                    f'Image dimensions ({image.width}x{image.height}) '
                    f'exceed maximum allowed ({self.max_width}x{self.max_height})'
                )
            if self.raise_exception and self.exception_class:
                raise self.exception_class(error_msg)
            return Result.Err(error_msg)
        return Result.Ok(True)


@dataclass(frozen=True, slots=True, kw_only=True)
class MaxSizeImageValidator(ImageValidator):
    """Validates that an image's file size does not exceed maximum allowed size in MB."""

    max_size: int | float  # in MB
    raise_exception: bool = False
    exception_class: type[Exception] | None = None
    error_message: str | None = None

    def __call__(self, image: AbsImage) -> Result[bool]:
        max_size_bytes = self.max_size * 1000000
        if image.size > max_size_bytes:
            if self.error_message:
                error_msg = self.error_message.format(
                    size=image.size,
                    max_size=self.max_size,
                )
            else:
                error_msg = (
                    f'Image size ({image.size} bytes) exceeds '
                    f'maximum allowed ({self.max_size} MB)'
                )
            if self.raise_exception and self.exception_class:
                raise self.exception_class(error_msg)
            return Result.Err(error_msg)
        return Result.Ok(True)


@dataclass(frozen=True, slots=True, kw_only=True)
class DjangoImageAdapter(AbsImage):
    """Adapter to convert Django image file objects to AbsImage protocol."""

    width: int | float
    height: int | float
    size: int | float


def django_image_validator(validator: ImageValidator):
    """Wraps an ImageValidator to work as a Django field validator."""

    def validate(image_file):
        if (
            hasattr(image_file, 'width')
            and hasattr(image_file, 'height')
            and hasattr(image_file, 'size')
        ):
            abs_image = DjangoImageAdapter(
                width=image_file.width, height=image_file.height, size=image_file.size
            )
            result = validator(abs_image)
            if result.is_err():
                raise ValidationError(result.unwrap_err().msg)

    return validate
