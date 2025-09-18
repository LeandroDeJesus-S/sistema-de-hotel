import pytest
from pydantic import ValidationError

from reservations.domain.entities import Room
from reservations.rules import RoomRules


@pytest.mark.parametrize(
    'number, adults_capacity, children_capacity, size, daily_price, image, short_desc, long_desc',
    [
        (
            '101',
            2,
            1,
            25,
            150.00,
            'room.jpg',
            'A cozy room',
            'A very cozy room with a view',
        ),
    ],
)
def test_room_creation_with_valid_data(
    number,
    adults_capacity,
    children_capacity,
    size,
    daily_price,
    image,
    short_desc,
    long_desc,
    hotel_fixture,
    room_class_fixture,
    benefits_fixture,
):
    # When
    room = Room(
        number=number,
        adults_capacity=adults_capacity,
        children_capacity=children_capacity,
        size=size,
        daily_price=daily_price,
        image=image,
        short_desc=short_desc,
        long_desc=long_desc,
        hotel=hotel_fixture,
        room_class=room_class_fixture,
        benefits=benefits_fixture,
    )

    # Then
    assert room.number == number
    assert room.adults_capacity == adults_capacity
    assert room.hotel == hotel_fixture


@pytest.mark.parametrize(
    'adults_capacity, children_capacity, size, daily_price, expected_error_message',
    [
        (
            RoomRules.MIN_ADULTS - 1,
            RoomRules.MIN_CHILDREN,
            RoomRules.MIN_SIZE,
            RoomRules.MIN_DAILY_PRICE,
            'adults_capacity',
        ),
        (
            RoomRules.MAX_ADULTS + 1,
            RoomRules.MIN_CHILDREN,
            RoomRules.MIN_SIZE,
            RoomRules.MIN_DAILY_PRICE,
            'adults_capacity',
        ),
    ],
)
def test_room_creation_with_invalid_data(
    adults_capacity,
    children_capacity,
    size,
    daily_price,
    expected_error_message,
    hotel_fixture,
    room_class_fixture,
    benefits_fixture,
):
    with pytest.raises(ValidationError) as excinfo:
        Room(
            number='101',
            adults_capacity=adults_capacity,
            children_capacity=children_capacity,
            size=size,
            daily_price=daily_price,
            image='room.jpg',
            short_desc='A cozy room',
            long_desc='A very cozy room with a view',
            hotel=hotel_fixture,
            room_class=room_class_fixture,
            benefits=benefits_fixture,
        )
    assert expected_error_message in str(excinfo.value)
