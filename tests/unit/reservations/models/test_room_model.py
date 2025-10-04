"""
Tests for the Room model.
"""

import pytest
from ddf import G, N
from django.core.exceptions import ValidationError

from reservations.feedback_messages import RoomErrorMessages
from reservations.models import Benefit, Room
from reservations.rules import RoomRules


@pytest.mark.django_db
def test_room_creation_with_valid_data(room_model, benefit_model):
    """
    Tests if a room is saved correctly to the database if the data is valid.
    """
    # Arrange
    room_model.benefits.add(benefit_model)

    # Assert
    assert Room.objects.filter(pk=room_model.pk).exists()
    assert room_model.benefits.first() == benefit_model


@pytest.mark.parametrize('number', ['AAAA', 'A123', '123a', '12AA', '12A'])
@pytest.mark.django_db
def test_invalid_room_number_raises_validation_error(number, room_model):
    """
    Tests if an invalid room number pattern raises a ValidationError.
    """
    # Arrange
    room_model.number = number

    # Act & Assert
    with pytest.raises(ValidationError):
        room_model.full_clean()


@pytest.mark.parametrize(
    'field, value, error_message',
    [
        (
            'adults_capacity',
            RoomRules.MIN_ADULTS - 1,
            RoomErrorMessages.ADULTS_INSUFFICIENT,
        ),
        (
            'children_capacity',
            RoomRules.MIN_CHILDREN - 1,
            RoomErrorMessages.CHILD_INSUFFICIENT,
        ),
        ('size', RoomRules.MIN_SIZE - 1, RoomErrorMessages.SIZE_INSUFFICIENT),
        (
            'daily_price',
            RoomRules.MIN_DAILY_PRICE - 1,
            RoomErrorMessages.PRICE_INSUFFICIENT,
        ),
    ],
)
@pytest.mark.django_db
def test_invalid_min_values_raise_validation_error(
    field, value, error_message, room_class_model, hotel_model
):
    # Arrange
    room = N(Room, room_class=room_class_model, hotel=hotel_model, **{field: value})

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        room.full_clean()
    assert error_message in excinfo.value.messages


@pytest.mark.parametrize(
    'field, value, error_message',
    [
        (
            'adults_capacity',
            RoomRules.MAX_ADULTS + 1,
            RoomErrorMessages.ADULTS_EXCEEDED,
        ),
        (
            'children_capacity',
            RoomRules.MAX_CHILDREN + 1,
            RoomErrorMessages.CHILD_EXCEEDED,
        ),
        ('size', RoomRules.MAX_SIZE + 1, RoomErrorMessages.SIZE_EXCEEDED),
        (
            'daily_price',
            RoomRules.MAX_DAILY_PRICE + 1,
            RoomErrorMessages.PRICE_EXCEEDED,
        ),
    ],
)
@pytest.mark.django_db
def test_invalid_max_values_raise_validation_error(
    field, value, error_message, room_class_model, hotel_model
):
    """
    Tests if adults_capacity, children_capacity, daily_price, and size raise a ValidationError
    if the maximum value is invalid.
    """
    # Arrange
    room = N(Room, room_class=room_class_model, hotel=hotel_model, **{field: value})

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        room.full_clean()
    assert error_message in excinfo.value.messages


@pytest.mark.django_db
def test_image_is_resized_on_save(room_class_model, hotel_model):
    """
    Tests if the image is resized correctly after saving.
    """
    # Arrange
    room = G(
        Room,
        room_class=room_class_model,
        hotel=hotel_model,
        image='test/room_test.jpg',
    )

    # Act
    # The object is already created and saved by ddf.

    # Assert
    assert (room.image.width, room.image.height) == RoomRules.IMAGE_SIZE


@pytest.mark.django_db
def test_invalid_image_name_raises_validation_error(room_model):
    """
    Tests if an invalid image name raises a ValidationError.
    """
    # Arrange
    room_model.image = 'test/room_test_inv@lid#.jpg'

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        room_model.full_clean()
    assert RoomErrorMessages.IMAGE_INVALID_NAME in excinfo.value.messages
