"""
Tests for the Reservation model.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from clients.models import Client
from reservations.models import Reservation, Room
from utils.supportmodels import ReserveErrorMessages, ReserveRules, RoomRules


@pytest.mark.django_db
def test_checkin_in_the_past_raises_validation_error(valid_reservation_data):
    """
    Tests if a ValidationError is raised when the check-in date is in the past.
    """
    # Arrange
    valid_reservation_data['checkin'] = datetime.now().date() - timedelta(days=1)
    reservation = Reservation(**valid_reservation_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        reservation.full_clean()
    assert ReserveErrorMessages.INVALID_CHECKIN_DATE in excinfo.value.messages


@pytest.mark.django_db
def test_checkin_too_far_in_future_raises_validation_error(valid_reservation_data):
    """
    Tests if a ValidationError is raised when the check-in date is too far in the future.
    """
    # Arrange
    valid_reservation_data['checkin'] = ReserveRules.checkin_anticipation_offset() + timedelta(
        days=1
    )
    valid_reservation_data['checkout'] = valid_reservation_data['checkin'] + timedelta(days=1)
    reservation = Reservation(**valid_reservation_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        reservation.full_clean()
    assert ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION in excinfo.value.messages


@pytest.mark.parametrize(
    'checkout_delta, error_message',
    [
        (timedelta(days=0), ReserveErrorMessages.INVALID_STAYED_DAYS),
        (
            timedelta(days=ReserveRules.MAX_RESERVATION_DAYS + 1),
            ReserveErrorMessages.INVALID_STAYED_DAYS,
        ),
    ],
)
@pytest.mark.django_db
def test_invalid_stay_duration_raises_validation_error(
    checkout_delta, error_message, valid_reservation_data
):
    """
    Tests if the minimum and maximum reservation duration raises a ValidationError when invalid.
    """
    # Arrange
    valid_reservation_data['checkout'] = valid_reservation_data['checkin'] + checkout_delta
    reservation = Reservation(**valid_reservation_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        reservation.full_clean()
    assert error_message in excinfo.value.messages


@pytest.mark.django_db
def test_reserving_unavailable_room_raises_validation_error(valid_reservation_data):
    """
    Tests if a ValidationError is raised when reserving an unavailable room.
    """
    # Arrange
    valid_reservation_data['room'].available = False
    reservation = Reservation(**valid_reservation_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        reservation.full_clean()
    assert ReserveErrorMessages.UNAVAILABLE_ROOM in excinfo.value.messages


@pytest.mark.django_db
def test_reservation_value_calculation(valid_reservation_data):
    """
    Tests if the reservation value is calculated correctly.
    """
    # Arrange
    valid_reservation_data['checkout'] = valid_reservation_data['checkin'] + timedelta(days=2)
    valid_reservation_data['room'].daily_price = Decimal('100')
    reservation = Reservation(**valid_reservation_data)

    # Act
    result = reservation.calc_reservation_value()

    # Assert
    assert result == Decimal('200')


@pytest.mark.django_db
def test_minimum_reservation_amount(valid_reservation_data):
    """
    Tests if the minimum reservation amount raises a ValidationError if it is less than the allowed value.
    """
    # Arrange
    valid_reservation_data['amount'] = Decimal(str(RoomRules.MIN_DAILY_PRICE - 1))
    reservation = Reservation(**valid_reservation_data)

    # Act & Assert
    with pytest.raises(ValidationError):
        reservation.full_clean()


@pytest.mark.django_db
def test_formatted_price(valid_reservation_data):
    """
    Tests if the formatted_price property returns the correctly formatted reservation value.
    """
    # Arrange
    valid_reservation_data['amount'] = Decimal('100')
    reservation = Reservation(**valid_reservation_data)

    # Act
    result = reservation.formatted_price()

    # Assert
    assert result == 'R$100.00'


@pytest.mark.django_db
def test_reservation_days_property(valid_reservation_data):
    """
    Tests if the reservation_days property returns the correct number of days.
    """
    # Arrange
    days = 4
    valid_reservation_data['checkout'] = valid_reservation_data['checkin'] + timedelta(
        days=days
    )
    reservation = Reservation(**valid_reservation_data)

    # Act & Assert
    assert reservation.reservation_days == days


@pytest.mark.django_db
def test_coast_in_cents_property(valid_reservation_data):
    """
    Tests if the coast_in_cents property returns the correct value in cents.
    """
    # Arrange
    valid_reservation_data['amount'] = Decimal('200')
    reservation = Reservation(**valid_reservation_data)

    # Act
    result = reservation.coast_in_cents

    # Assert
    assert result == 20000


@pytest.mark.django_db
def test_default_status_is_initiated(valid_reservation_data):
    """
    Tests if the initial status of the reservation is 'I' (initiated).
    """
    # Arrange
    reservation = Reservation(**valid_reservation_data)

    # Act
    reservation.save()

    # Assert
    assert reservation.status == 'I'


@pytest.mark.django_db
def test_reservation_is_inactive_on_creation(valid_reservation_data):
    """
    Tests if the reservation is inactive when created.
    """
    # Arrange
    reservation = Reservation(**valid_reservation_data)

    # Act
    reservation.save()

    # Assert
    assert not reservation.active


@pytest.mark.django_db
def test_creating_overlapping_reservation_raises_validation_error(db_setup):
    """
    Tests if a ValidationError is raised if a reservation overlaps with an active one.
    """
    # Arrange
    client1 = Client.objects.get(pk=1)
    client2 = Client.objects.get(pk=2)
    room = Room.objects.get(pk=1)
    checkin = datetime.now().date()
    checkout = checkin + timedelta(days=5)

    Reservation.objects.create(
        client=client1, room=room, checkin=checkin, checkout=checkout, active=True, status='A'
    )

    overlapping_reservation = Reservation(
        client=client2,
        room=room,
        checkin=checkin + timedelta(days=1),
        checkout=checkout + timedelta(days=1),
    )

    # Act & Assert
    with pytest.raises(ValidationError):
        overlapping_reservation.full_clean()


@pytest.mark.django_db
def test_available_dates_returns_correct_string(valid_reservation_data):
    """
    Tests if the available_dates method returns the correct string of available dates.
    """
    # Arrange
    reservation1 = Reservation.objects.create(
        **valid_reservation_data, active=True, status='A'
    )

    checkin2 = reservation1.checkout + timedelta(days=2)
    checkout2 = checkin2 + timedelta(days=1)

    reservation2_data = valid_reservation_data.copy()
    reservation2_data['checkin'] = checkin2
    reservation2_data['checkout'] = checkout2
    reservation2_data['status'] = 'S'
    reservation2 = Reservation.objects.create(**reservation2_data)

    date_1 = reservation1.checkout.strftime('%d/%m/%Y')
    date_2 = (reservation2.checkin - timedelta(days=1)).strftime('%d/%m/%Y')
    date_3 = reservation2.checkout.strftime('%d/%m/%Y')

    expected = f'{date_1} a {date_2}, e {date_3} para frente.'

    # Act
    result = Reservation.available_dates(valid_reservation_data['room'])

    # Assert
    assert result == expected
