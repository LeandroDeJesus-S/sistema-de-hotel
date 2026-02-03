import pytest
from reservations.domain.entities import Room
from reservations.domain.value_objects import PriceValue, Currency
from reservations.feedback_messages import RoomErrorMessages


class TestRoom:
    """Tests for Room entity."""

    def test_room_available_without_prices_returns_error(
        self, hotel_entity, room_class_entity
    ):
        """Should return error when creating room with available=True and no prices."""
        room_result = Room.safe_create(
            number='101A',
            adults_capacity=2,
            children_capacity=1,
            size=25,
            short_desc='Nice room',
            long_desc='Very nice room with view',
            room_class=room_class_entity,
            hotel=hotel_entity,
            available=True,  # Trying to set as available
            prices=[],  # But no prices provided
        )

        assert room_result.is_err()
        assert (
            'Room must have at least one price to be available' in room_result.unwrap_err().msg
        )

    def test_room_available_with_prices_succeeds(
        self, hotel_entity, room_class_entity, price_entity
    ):
        """Should allow room to be available when it has at least one price."""
        room_result = Room.safe_create(
            number='102A',
            adults_capacity=2,
            children_capacity=1,
            size=30,
            short_desc='Nice room with price',
            long_desc='Room with price available',
            room_class=room_class_entity,
            hotel=hotel_entity,
            available=True,
            prices=[price_entity],
        )

        assert room_result.is_ok()
        room = room_result.unwrap()
        assert room.available is True
        assert room.prices == [price_entity]

    def test_room_unavailable_without_prices_succeeds(self, hotel_entity, room_class_entity):
        """Should allow room to be unavailable when it has no prices."""
        room_result = Room.safe_create(
            number='103A',
            adults_capacity=2,
            children_capacity=1,
            size=20,
            short_desc='Unavailable room',
            long_desc='Room not available',
            room_class=room_class_entity,
            hotel=hotel_entity,
            available=False,
            prices=[],
        )

        assert room_result.is_ok()
        room = room_result.unwrap()
        assert room.available is False
        assert room.prices == []

    def test_room_unavailable_with_prices_succeeds(
        self, hotel_entity, room_class_entity, price_entity
    ):
        """Should allow room to be unavailable even when it has prices."""
        room_result = Room.safe_create(
            number='104A',
            adults_capacity=3,
            children_capacity=2,
            size=25,  # Within MAX_SIZE=30
            short_desc='Unavailable room with prices',
            long_desc='Room with prices but unavailable',
            room_class=room_class_entity,
            hotel=hotel_entity,
            available=False,
            prices=[price_entity],
        )

        assert room_result.is_ok()
        room = room_result.unwrap()
        assert room.available is False
        assert room.prices == [price_entity]

    def test_room_validation_works_with_existing_entity(self, room_entity, price_entity):
        """Should apply validation when modifying existing room entity."""
        # Start with unavailable room without prices
        assert room_entity.available is False
        assert room_entity.prices == []

        # Try to set it as available without prices
        room_entity.available = True

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            room_entity.validate_prices_for_availability()

        assert 'Room must have at least one price to be available' in str(exc_info.value)

        # Add prices and try again
        room_entity.prices = [price_entity]
        room_entity.available = True
        validated_room = room_entity.validate_prices_for_availability()

        # Should stay True now
        assert validated_room.available is True

    def test_room_str_representation(self, room_entity):
        """Should return correct string representation."""
        expected = f'{room_entity.number} - {room_entity.room_class.name}'
        assert str(room_entity) == expected
