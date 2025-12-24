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


def validate_benefit_icon(image_file):
    """Django validator for benefit icons (64x64 max, 5MB max)."""
    if (
        hasattr(image_file, 'width')
        and hasattr(image_file, 'height')
        and hasattr(image_file, 'size')
    ):
        abs_image = DjangoImageAdapter(
            width=image_file.width, height=image_file.height, size=image_file.size
        )

        # Check dimensions
        dim_validator = MaxDimensionsImageValidator(
            max_width=64,
            max_height=64,
            raise_exception=False,
            error_message='O ícone deve ter tamanho 64x64.',
        )
        dim_result = dim_validator(abs_image)
        if dim_result.is_err():
            raise ValidationError(dim_result.unwrap_err().msg)

        # Check file size (5MB)
        size_validator = MaxSizeImageValidator(max_size=5, raise_exception=False)
        size_result = size_validator(abs_image)
        if size_result.is_err():
            raise ValidationError(size_result.unwrap_err().msg)


def validate_service_logo(image_file):
    """Django validator for service logos (5MB max)."""
    if hasattr(image_file, 'size'):
        abs_image = DjangoImageAdapter(
            width=getattr(image_file, 'width', 0),
            height=getattr(image_file, 'height', 0),
            size=image_file.size,
        )

        # Check file size (5MB)
        size_validator = MaxSizeImageValidator(max_size=5, raise_exception=False)
        size_result = size_validator(abs_image)
        if size_result.is_err():
            raise ValidationError(size_result.unwrap_err().msg)


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
