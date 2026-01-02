"""
Tests for the Payment model.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from payments.error_messages import PaymentErrorMessages
from payments.models import Payment


@pytest.mark.django_db
def test_payment_creation_date_is_set(payment_model):
    """
    Tests if the payment creation date is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_model

    # Act & Assert
    assert payment.created_at.timestamp() == pytest.approx(datetime.now().timestamp(), abs=1)


@pytest.mark.django_db
def test_client_is_assigned_to_payment(payment_model, client_model):
    """
    Tests if the client is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_model

    # Act & Assert
    assert payment.reservation.client == client_model


@pytest.mark.django_db
def test_room_is_assigned_to_payment(payment_model, room_model):
    """
    Tests if the room is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_model

    # Act & Assert
    assert payment.reservation.room == room_model


@pytest.mark.django_db
def test_amount_is_assigned_to_payment(payment_model, reservation_model):
    """
    Tests if the total amount to be paid is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_model

    # Act & Assert
    assert payment.amount == reservation_model.amount


@pytest.mark.django_db
def test_reservation_is_assigned_to_payment(payment_model, reservation_model):
    """
    Tests if the reservation is correctly assigned to the payment.
    """
    # Arrange
    payment = payment_model

    # Act & Assert
    assert payment.reservation == reservation_model


@pytest.mark.django_db
def test_initial_status_is_processing(payment_model):
    """
    Tests if the status when starting the payment is 'PENDING'.
    """
    # Arrange
    payment = payment_model

    # Act & Assert
    assert payment.status == Payment.Status.PENDING


@pytest.mark.django_db
def test_validation_error_if_payment_amount_differs_from_reservation(reservation_model):
    """
    Tests if a ValidationError is raised if the payment amount is different from the reservation amount.
    """
    # Arrange
    payment = Payment(
        client=reservation_model.client,
        reservation=reservation_model,
        amount=Decimal('10000'),
    )

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        payment.full_clean()
    assert PaymentErrorMessages.INVALID_PAYMENT_VALUE in excinfo.value.messages


@pytest.mark.django_db
def test_payment_saved_with_valid_data(reservation_model):
    """
    Tests if the payment is persisted with all valid data.
    """
    # Arrange
    payment = Payment(
        client=reservation_model.client,
        reservation=reservation_model,
        amount=reservation_model.amount,
    )

    # Act
    payment.full_clean()
    payment.save()

    # Assert
    assert Payment.objects.last() == payment
