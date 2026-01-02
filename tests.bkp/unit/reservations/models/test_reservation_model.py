"""
Tests for the Reservation model.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from ddf import G, N
from django.core.exceptions import ValidationError

from clients.models import Client
from reservations.feedback_messages import ReserveErrorMessages
from reservations.models import Reservation
from reservations.rules import ReserveRules, RoomRules


@pytest.mark.django_db
def test_checkin_in_the_past_raises_validation_error(client_model, room_model):
    """
    Tests if a ValidationError is raised when the check-in date is in the past.
    """
    # Arrange
    checkin = datetime.now().date() - timedelta(days=1)
    checkout = checkin + timedelta(days=5)
    reservation = Reservation(
        client=client_model,
        room=room_model,
        checkin=checkin,
        checkout=checkout,
        amount=Decimal('500.00'),
    )

    # Act & Assert
    with pytest.raises(ValidationError):
        reservation.full_clean()


@pytest.mark.django_db
def test_checkin_too_far_in_future_raises_validation_error(client_model, room_model):
    """
    Tests if a ValidationError is raised when the check-in date is too far in the future.
    """
    # Arrange
    checkin = ReserveRules.checkin_anticipation_offset() + timedelta(days=1)
    checkout = checkin + timedelta(days=1)
    reservation = Reservation(
        client=client_model,
        room=room_model,
        checkin=checkin,
        checkout=checkout,
        amount=Decimal('500.00'),
    )

    # Act & Assert
    with pytest.raises(ValidationError):
        reservation.full_clean()


@pytest.mark.parametrize(
    'checkout_delta, error_message',
    [
        (timedelta(days=ReserveRules.MIN_RESERVATION_DAYS - 1), ReserveErrorMessages.INVALID_STAYED_DAYS),
        (
            timedelta(days=ReserveRules.MAX_RESERVATION_DAYS + 1),
            ReserveErrorMessages.INVALID_STAYED_DAYS,
        ),
    ],
)
@pytest.mark.django_db
def test_invalid_stay_duration_raises_validation_error(
    checkout_delta, error_message, reservation_model
):
    """
    Tests if the minimum and maximum reservation duration raises a ValidationError when invalid.
    """
    # Arrange
    reservation_model.checkin = datetime.now().date()
    reservation_model.checkout = reservation_model.checkin + checkout_delta

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        reservation_model.full_clean()
    assert any(str(error_message) in msg for msg in excinfo.value.messages), excinfo.value.messages


@pytest.mark.django_db
def test_reservation_value_calculation(reservation_model):
    """
    Tests if the reservation value is calculated correctly.
    """
    # Arrange
    reservation_model.checkout = reservation_model.checkin + timedelta(days=2)
    reservation_model.room.daily_price = Decimal('100')

    # Act
    result = reservation_model.calc_reservation_value()

    # Assert
    assert result == Decimal('200')


@pytest.mark.django_db
def test_minimum_reservation_amount(reservation_model):
    """
    Tests if the minimum reservation amount raises a ValidationError if it is less than the allowed value.
    """
    # Arrange
    reservation_model.amount = Decimal(str(RoomRules.MIN_DAILY_PRICE - 1))

    # Act & Assert
    with pytest.raises(ValidationError):
        reservation_model.full_clean()


@pytest.mark.django_db
def test_formatted_price(reservation_model):
    """
    Tests if the formatted_price property returns the correctly formatted reservation value.
    """
    # Arrange
    reservation_model.amount = Decimal('100')

    # Act
    result = reservation_model.formatted_price()

    # Assert
    assert result == 'R$100.00'


@pytest.mark.django_db
def test_reservation_days_property(reservation_model):
    """
    Tests if the reservation_days property returns the correct number of days.
    """
    # Arrange
    days = 4
    reservation_model.checkout = reservation_model.checkin + timedelta(days=days)

    # Act & Assert
    assert reservation_model.reservation_days == days


@pytest.mark.django_db
def test_coast_in_cents_property(reservation_model):
    """
    Tests if the coast_in_cents property returns the correct value in cents.
    """
    # Arrange
    reservation_model.amount = Decimal('200')

    # Act
    result = reservation_model.coast_in_cents

    # Assert
    assert result == 20000


@pytest.mark.django_db
def test_default_status_is_initiated(client_model, room_model):
    """
    Tests if the initial status of the reservation is 'I' (initiated).
    """
    # Arrange
    checkin = datetime.now().date()
    checkout = checkin + timedelta(days=5)
    reservation = Reservation(
        client=client_model,
        room=room_model,
        checkin=checkin,
        checkout=checkout,
        amount=Decimal('500.00'),
    )

    # Act
    reservation.save()

    # Assert
    assert reservation.status == 'I'


@pytest.mark.django_db
def test_creating_overlapping_reservation_raises_validation_error(reservation_model, faker):
    """
    Tests if a ValidationError is raised if a reservation overlaps with an active one.
    """
    # Arrange
    from clients.rules import ClientRules
    client2 = G(Client, birthdate=faker.date_of_birth(minimum_age=ClientRules.MIN_AGE + 1, maximum_age=ClientRules.MAX_AGE - 1))

    overlapping_reservation = N(
        Reservation,
        client=client2,
        room=reservation_model.room,
        checkin=reservation_model.checkin + timedelta(days=1),
        checkout=reservation_model.checkout + timedelta(days=1),
    )

    # Act & Assert
    with pytest.raises(ValidationError):
        overlapping_reservation.full_clean()
