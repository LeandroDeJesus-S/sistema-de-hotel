"""
Tests for the payments tasks.
"""

import pytest

from payments import models, tasks


@pytest.mark.django_db
def test_create_payment_pdf_sends_email_with_valid_payment(db_setup, mocker):
    """
    Tests if the task returns True if the email is sent correctly with a valid payment.
    """
    # Arrange
    payment = models.Payment.objects.first()
    mock_pdf_handler = mocker.patch('payments.tasks.PaymentPDFHandler')
    mock_pdf_handler.handle.side_effect = 1

    # Act
    result = tasks.create_payment_pdf(payment)

    # Assert
    assert result


@pytest.mark.django_db
def test_create_payment_pdf_returns_false_if_email_not_sent(db_setup, mocker):
    """
    Tests if the task returns False if the email is not sent correctly with a valid payment.
    """
    # Arrange
    payment = models.Payment.objects.first()
    mock_pdf_handler = mocker.patch('payments.tasks.PaymentPDFHandler.handle')
    mock_pdf_handler.return_value = 0

    # Act
    result = tasks.create_payment_pdf(payment)

    # Assert
    assert not result
