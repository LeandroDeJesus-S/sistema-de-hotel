import pytest
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import models
from utils.adapters.image_validators import (
    MaxDimensionsImageValidator,
    MaxSizeImageValidator,
    django_image_validator,
)
from base.ports.image_validator import AbsImage
from typing import Union


@dataclass(frozen=True, slots=True, kw_only=True)
class MockImage(AbsImage):
    width: Union[int, float]
    height: Union[int, float]
    size: Union[int, float] = 100


class CustomImageDimensionError(Exception):
    pass


class MockImageFile:
    """Mock Django image file with width, height, size."""

    def __init__(self, width: int, height: int, size: int):
        self.width = width
        self.height = height
        self.size = size


def test_image_dimensions_within_limits():
    """Tests that the validator returns Ok(True) when image dimensions are within limits."""
    validator = MaxDimensionsImageValidator(max_width=100, max_height=100)
    image = MockImage(width=50, height=50)
    result = validator(image)
    assert result.is_ok()
    assert result.unwrap() is True


def test_image_dimensions_exceed_limits_no_exception():
    """Tests that the validator returns an Err result when dimensions exceed limits and no exception is raised."""
    validator = MaxDimensionsImageValidator(max_width=100, max_height=100)
    image = MockImage(width=150, height=50)
    result = validator(image)
    assert result.is_err()
    assert (
        'Image dimensions (150x50) exceed maximum allowed (100x100)' in result.unwrap_err().msg
    )

    image = MockImage(width=50, height=150)
    result = validator(image)
    assert result.is_err()
    assert (
        'Image dimensions (50x150) exceed maximum allowed (100x100)' in result.unwrap_err().msg
    )

    image = MockImage(width=150, height=150)
    result = validator(image)
    assert result.is_err()
    assert (
        'Image dimensions (150x150) exceed maximum allowed (100x100)'
        in result.unwrap_err().msg
    )


def test_image_size_within_limits():
    """Tests that the validator returns Ok(True) when image size is within limits."""
    validator = MaxSizeImageValidator(max_size=1)  # 1 MB
    image = MockImage(width=50, height=50, size=500000)  # 0.5 MB
    result = validator(image)
    assert result.is_ok()
    assert result.unwrap() is True


def test_image_size_exceed_limits_no_exception():
    """Tests that the validator returns an Err result when size exceeds limits and no exception is raised."""
    validator = MaxSizeImageValidator(max_size=1)  # 1 MB
    image = MockImage(width=50, height=50, size=1500000)  # 1.5 MB
    result = validator(image)
    assert result.is_err()
    assert (
        'Image size (1500000 bytes) exceeds maximum allowed (1 MB)' in result.unwrap_err().msg
    )


def test_image_size_exceed_limits_with_exception():
    """Tests that the validator raises the specified exception when size exceeds limits and raise_exception is True."""
    validator = MaxSizeImageValidator(
        max_size=1,  # 1 MB
        raise_exception=True,
        exception_class=CustomImageDimensionError,
    )
    image = MockImage(width=50, height=50, size=1500000)  # 1.5 MB
    with pytest.raises(CustomImageDimensionError) as exc_info:
        validator(image)
    assert 'Image size (1500000 bytes) exceeds maximum allowed (1 MB)' in str(exc_info.value)


def test_image_size_at_limits():
    """Tests that the validator returns Ok(True) when image size is exactly at the maximum limit."""
    validator = MaxSizeImageValidator(max_size=1)  # 1 MB
    image = MockImage(width=50, height=50, size=1000000)  # 1 MB
    result = validator(image)
    assert result.is_ok()
    assert result.unwrap() is True


def test_max_dimensions_validator_with_custom_error_message():
    """Tests that MaxDimensionsImageValidator uses a custom error message with placeholders."""
    validator = MaxDimensionsImageValidator(
        max_width=100,
        max_height=100,
        error_message='Custom error: Image is {width}x{height}, but max is {max_width}x{max_height}',
    )
    image = MockImage(width=150, height=50)
    result = validator(image)
    assert result.is_err()
    assert 'Custom error: Image is 150x50, but max is 100x100' in result.unwrap_err().msg


def test_max_size_validator_with_custom_error_message():
    """Tests that MaxSizeImageValidator uses a custom error message with placeholders."""
    validator = MaxSizeImageValidator(
        max_size=1,  # 1 MB
        error_message='File too big: {size} bytes, limit is {max_size} MB',
    )
    image = MockImage(width=50, height=50, size=1500000)  # 1.5 MB
    result = validator(image)
    assert result.is_err()
    assert 'File too big: 1500000 bytes, limit is 1 MB' in result.unwrap_err().msg


def test_max_dimensions_validator_with_django_model_raises_validation_error():
    """Tests that MaxDimensionsImageValidator raises ValidationError in a Django model when dimensions exceed limits."""
    validator = MaxDimensionsImageValidator(max_width=100, max_height=100)

    class TestModel(models.Model):
        image = models.ImageField(validators=[django_image_validator(validator)])

        class Meta:
            app_label = 'test_validators'

    model_instance = TestModel()
    model_instance.image = MockImageFile(width=150, height=50, size=1000)
    with pytest.raises(ValidationError) as exc_info:
        model_instance.full_clean()
    assert 'Image dimensions (150x50) exceed maximum allowed (100x100)' in str(exc_info.value)


def test_max_size_validator_with_django_model_raises_validation_error():
    """Tests that MaxSizeImageValidator raises ValidationError in a Django model when size exceeds limits."""
    validator = MaxSizeImageValidator(max_size=1)  # 1 MB

    class TestModel(models.Model):
        image = models.ImageField(validators=[django_image_validator(validator)])

        class Meta:
            app_label = 'test_validators'

    model_instance = TestModel()
    model_instance.image = MockImageFile(width=50, height=50, size=1500000)  # 1.5 MB
    with pytest.raises(ValidationError) as exc_info:
        model_instance.full_clean()
    assert 'Image size (1500000 bytes) exceeds maximum allowed (1 MB)' in str(exc_info.value)


def test_image_dimensions_at_limits():
    """Tests that the validator returns Ok(True) when image dimensions are exactly at the maximum limits."""
    validator = MaxDimensionsImageValidator(max_width=100, max_height=100)
    image = MockImage(width=100, height=100)
    result = validator(image)
    assert result.is_ok()
    assert result.unwrap() is True


def test_image_dimensions_one_exceeds_one_at_limit():
    """Tests that the validator returns an Err result when one dimension exceeds the limit and the other is at the limit."""
    validator = MaxDimensionsImageValidator(max_width=100, max_height=100)
    image = MockImage(width=100, height=150)
    result = validator(image)
    assert result.is_err()
    assert (
        'Image dimensions (100x150) exceed maximum allowed (100x100)'
        in result.unwrap_err().msg
    )

    image = MockImage(width=150, height=100)
    result = validator(image)
    assert result.is_err()
    assert (
        'Image dimensions (150x100) exceed maximum allowed (100x100)'
        in result.unwrap_err().msg
    )
