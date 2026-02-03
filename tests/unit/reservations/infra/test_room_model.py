import pytest
from django.core.exceptions import ValidationError
from reservations.models import Room, Class, Hotel, Price, Benefit


class TestRoomModel:
    """Tests for Room model validation."""

    def test_clean_available_without_prices_raises_error(
        self, hotel_model_instance, room_class_model_instance
    ):
        """Should raise ValidationError when room is available without prices."""
        room = Room(
            room_class=room_class_model_instance,
            number='101A',
            adults_capacity=2,
            children_capacity=1,
            size=25,
            available=True,  # Trying to set as available
            hotel=hotel_model_instance,
            short_desc='Test room',
        )
        # Save room first to get an ID
        room.save()

        # Run clean method - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            room.clean()

        # Check that error message is correct
        assert '__all__' in exc_info.value.error_dict
        error_msg = exc_info.value.error_dict['__all__'][0]
        assert 'Room must have at least one price to be available' in str(error_msg)

    def test_clean_available_with_prices_succeeds(
        self, hotel_model_instance, room_class_model_instance
    ):
        """Should allow room to be available when it has at least one price."""
        room = Room(
            room_class=room_class_model_instance,
            number='102A',
            adults_capacity=2,
            children_capacity=1,
            size=30,
            available=True,
            hotel=hotel_model_instance,
            short_desc='Test room with price',
        )
        # Save the room first to get an ID
        room.save()
        # Create and add a price
        price = Price.objects.create(currency='usd', value=20000, active=True)
        room.prices.add(price)  # Add price to ManyToManyField

        # Run clean method - should not raise error
        room.clean()

        # Should remain available
        assert room.available is True

    def test_clean_unavailable_without_prices_succeeds(
        self, hotel_model_instance, room_class_model_instance
    ):
        """Should allow room to be unavailable when it has no prices."""
        room = Room(
            room_class=room_class_model_instance,
            number='103A',
            adults_capacity=2,
            children_capacity=1,
            size=20,
            available=False,
            hotel=hotel_model_instance,
            short_desc='Unavailable room',
        )
        # Save the room first to get an ID
        room.save()

        # Run clean method - should not raise error
        room.clean()

        # Should remain unavailable
        assert room.available is False

    def test_clean_raises_validation_error_for_available_without_prices_duplicate(
        self, hotel_model_instance, room_class_model_instance
    ):
        """Should raise ValidationError when room is available without prices."""
        room = Room(
            room_class=room_class_model_instance,
            number='104A',
            adults_capacity=2,
            children_capacity=1,
            size=25,
            available=True,
            hotel=hotel_model_instance,
            short_desc='Room that should raise error',
        )
        # Save room first to get an ID
        room.save()

        # Run clean method - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            room.clean()

        # Check that error message is correct
        assert '__all__' in exc_info.value.error_dict
        error_msg = exc_info.value.error_dict['__all__'][0]
        assert 'Room must have at least one price to be available' in str(error_msg)

    def test_clean_prices_validation_only(
        self, hotel_model_instance, room_class_model_instance
    ):
        """Should raise ValidationError for prices without image issues."""
        room = Room(
            room_class=room_class_model_instance,
            number='105A',
            adults_capacity=2,
            children_capacity=1,
            size=25,
            available=True,  # No prices - should trigger prices error
            hotel=hotel_model_instance,
            short_desc='Test room',
            image=None,  # No image to avoid middleware issues
        )
        # Save room first to get an ID
        room.save()

        # Run clean method - should raise ValidationError with prices error
        with pytest.raises(ValidationError) as exc_info:
            room.clean()

        # Check that prices error is present
        assert '__all__' in exc_info.value.error_dict
        prices_error = exc_info.value.error_dict['__all__'][0]
        assert 'Room must have at least one price to be available' in str(prices_error)

    def test_full_clean_integration(self, hotel_model_instance, room_class_model_instance):
        """Test that full_clean() properly calls clean() and validates all fields."""
        room = Room(
            room_class=room_class_model_instance,
            number='106A',
            adults_capacity=2,
            children_capacity=1,
            size=25,
            available=True,  # No prices - should raise error
            hotel=hotel_model_instance,
            short_desc='Test room for full_clean',
        )
        # Save room first to get an ID
        room.save()

        # Run full_clean - should raise ValidationError from clean()
        with pytest.raises(ValidationError) as exc_info:
            room.full_clean()

        # Check that validation error includes prices error
        assert '__all__' in exc_info.value.error_dict
        error_msg = exc_info.value.error_dict['__all__'][0]
        assert 'Room must have at least one price to be available' in str(error_msg)

    def test_room_str_representation(self, hotel_model_instance, room_class_model_instance):
        """Should return correct string representation."""
        room = Room(
            room_class=room_class_model_instance,
            number='107A',
            adults_capacity=2,
            children_capacity=1,
            size=25,
            available=False,
            hotel=hotel_model_instance,
            short_desc='Test room for str',
        )

        expected = f'Nº{room.number} {room.room_class}'
        assert str(room) == expected
