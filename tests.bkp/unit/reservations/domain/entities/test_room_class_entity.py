import pytest
from pydantic import ValidationError

from reservations.domain.entities import RoomClass


@pytest.mark.parametrize(
    'name',
    [
        'Standard',
        'Deluxe',
    ],
)
def test_room_class_creation_with_valid_data(name):
    # When
    room_class = RoomClass(name=name)

    # Then
    assert room_class.name == name


@pytest.mark.parametrize(
    'name',
    [
        '',
    ],
)
def test_room_class_creation_with_invalid_data(name):
    # When / Then
    with pytest.raises(ValidationError):
        RoomClass(name=name)
