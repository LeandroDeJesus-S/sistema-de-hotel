"""
Tests for the Room model.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from reservations.models import Benefit, Class, Room
from utils.supportmodels import RoomErrorMessages, RoomRules





@pytest.mark.django_db
def test_room_creation_with_valid_data(valid_room_data):
    """
    Tests if a room is saved correctly to the database if the data is valid.
    """
    # Arrange
    room = Room(**valid_room_data)

    # Act
    room.full_clean()
    room.save()
    room.benefit.add(Benefit.objects.first())

    # Assert
    assert Room.objects.filter(pk=room.pk).exists()


@pytest.mark.parametrize(
    "number",
    [
        'AAAA',
        'A123',
        '123a',
        '12AA',
        '12A'
    ]
)
@pytest.mark.django_db
def test_invalid_room_number_raises_validation_error(number, valid_room_data):
    """
    Tests if an invalid room number pattern raises a ValidationError.
    """
    # Arrange
    valid_room_data['number'] = number
    room = Room(**valid_room_data)

    # Act & Assert
    with pytest.raises(ValidationError):
        room.full_clean()


@pytest.mark.parametrize(
    "field, value, error_message",
    [
        ('adult_capacity', RoomRules.MIN_ADULTS - 1, RoomErrorMessages.ADULTS_INSUFFICIENT),
        ('child_capacity', RoomRules.MIN_CHILDREN - 1, RoomErrorMessages.CHILD_INSUFFICIENT),
        ('size', RoomRules.MIN_SIZE - 1, RoomErrorMessages.SIZE_INSUFFICIENT),
        ('daily_price', RoomRules.MIN_DAILY_PRICE - 1, RoomErrorMessages.PRICE_INSUFFICIENT),
    ]
)
@pytest.mark.django_db
def test_invalid_min_values_raise_validation_error(field, value, error_message, valid_room_data):
    """
    Tests if adult_capacity, child_capacity, size, and daily_price raise a ValidationError
    if the minimum value is invalid.
    """
    # Arrange
    valid_room_data[field] = value
    room = Room(**valid_room_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        room.full_clean()
    assert error_message in excinfo.value.messages


@pytest.mark.parametrize(
    "field, value, error_message",
    [
        ('adult_capacity', RoomRules.MAX_ADULTS + 1, RoomErrorMessages.ADULTS_EXCEEDED),
        ('child_capacity', RoomRules.MAX_CHILDREN + 1, RoomErrorMessages.CHILD_EXCEEDED),
        ('size', RoomRules.MAX_SIZE + 1, RoomErrorMessages.SIZE_EXCEEDED),
        ('daily_price', RoomRules.MAX_DAILY_PRICE + 1, RoomErrorMessages.PRICE_EXCEEDED),
    ]
)
@pytest.mark.django_db
def test_invalid_max_values_raise_validation_error(field, value, error_message, valid_room_data):
    """
    Tests if adult_capacity, child_capacity, daily_price, and size raise a ValidationError
    if the maximum value is invalid.
    """
    # Arrange
    valid_room_data[field] = value
    room = Room(**valid_room_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        room.full_clean()
    assert error_message in excinfo.value.messages


@pytest.mark.django_db
def test_image_is_resized_on_save(valid_room_data):
    """
    Tests if the image is resized correctly after saving.
    """
    # Arrange
    room = Room(**valid_room_data)

    # Act
    room.save()

    # Assert
    assert (room.image.width, room.image.height) == RoomRules.IMAGE_SIZE


@pytest.mark.django_db
def test_invalid_image_name_raises_validation_error(valid_room_data):
    """
    Tests if an invalid image name raises a ValidationError.
    """
    # Arrange
    valid_room_data['image'] = 'test/room_test_inv@lid#.jpg'
    room = Room(**valid_room_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        room.full_clean()
    assert RoomErrorMessages.IMAGE_INVALID_NAME in excinfo.value.messages


@pytest.mark.django_db
def test_daily_price_formatted(valid_room_data):
    """
    Tests if the daily_price_formatted method returns the formatted price.
    """
    # Arrange
    room = Room(**valid_room_data)

    # Act
    result = room.daily_price_formatted()

    # Assert
    assert result == 'R$100.00'


@pytest.mark.django_db
def test_daily_price_in_cents(valid_room_data):
    """
    Tests if the daily_price_in_cents property returns the price in cents.
    """
    # Arrange
    room = Room(**valid_room_data)

    # Act
    result = room.daily_price_in_cents

    # Assert
    assert result == 10000


@pytest.mark.django_db
def test_room_str_method(valid_room_data):
    """
    Tests if the __str__ method returns the correct value.
    """
    # Arrange
    room = Room(**valid_room_data)

    # Act
    result = str(room)

    # Assert
    assert result == f'Nº{room.number} {room.room_class}'
