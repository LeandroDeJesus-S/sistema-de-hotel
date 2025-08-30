"""
Tests for the Payment model.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from clients.models import Client
from payments.models import Payment
from reservations.models import Reservation, Room
from utils.supportmodels import PaymentErrorMessages


@pytest.mark.django_db
def test_payment_creation_date_is_set(payment_data):
    """
    Tests if the payment creation date is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_data['payment']

    # Act & Assert
    assert payment.date.timestamp() == pytest.approx(datetime.now().timestamp(), abs=0.01)


@pytest.mark.django_db
def test_client_is_assigned_to_payment(payment_data):
    """
    Tests if the client is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_data['payment']
    user = payment_data['user']

    # Act & Assert
    assert payment.reservation.client == user


@pytest.mark.django_db
def test_room_is_assigned_to_payment(payment_data):
    """
    Tests if the room is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_data['payment']
    room = payment_data['room']

    # Act & Assert
    assert payment.reservation.room == room


@pytest.mark.django_db
def test_amount_is_assigned_to_payment(payment_data):
    """
    Tests if the total amount to be paid is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_data['payment']
    reservation = payment_data['reservation']

    # Act & Assert
    assert payment.amount == reservation.amount


@pytest.mark.django_db
def test_reservation_is_assigned_to_payment(payment_data):
    """
    Tests if the reservation is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_data['payment']
    reservation = payment_data['reservation']

    # Act & Assert
    assert payment.reservation == reservation


@pytest.mark.django_db
def test_initial_status_is_processing(payment_data):
    """
    Tests if the status when starting the payment is 'P' for processing.
    """
    # Arrange
    payment = payment_data['payment']

    # Act & Assert
    assert payment.status == 'P'


@pytest.mark.django_db
def test_validation_error_if_payment_amount_differs_from_reservation(payment_data):
    """
    Tests if a ValidationError is raised if the payment amount is different from the reservation amount.
    """
    # Arrange
    reservation = payment_data['reservation']
    payment = Payment(reservation=reservation, amount=Decimal('10000'))

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        payment.full_clean()
    assert PaymentErrorMessages.INVALID_PAYMENT_VALUE in excinfo.value.messages


@pytest.mark.django_db
def test_payment_saved_with_valid_data(db_setup):
    """
    Tests if the payment is persisted with all valid data.
    """
    # Arrange
    room = Room.objects.get(pk=1)
    reservation = Reservation.objects.create(
        client=Client.objects.first(),
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
        amount=Decimal(str(room.daily_price)),
        observations='*' * 100,
        room=room,
    )
    payment = Payment(reservation=reservation, amount=reservation.amount)

    # Act
    payment.full_clean()
    payment.save()

    # Assert
    assert Payment.objects.last() == payment
