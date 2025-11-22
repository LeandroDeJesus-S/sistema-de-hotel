"""
Tests for the payments tasks.
"""

from unittest.mock import MagicMock

import pytest

from base.ports.email import AbsEmailSender
from base.ports.pdf import AbsPDFGenerator
from exc import Result
from payments import models, tasks
from payments.domain.entities import Payment as PaymentEntity
from utils.support import model_to_entity


@pytest.mark.django_db
def test_send_payment_confirmation_sends_email_with_valid_payment_id(payment_model, mocker):
    """
    Tests if the task returns True if the email is sent correctly with a valid payment ID.
    """
    # Arrange
    payment_entity = model_to_entity(payment_model, PaymentEntity).unwrap()

    mock_pdf_generator = mocker.MagicMock(spec=AbsPDFGenerator)
    mock_pdf_generator.generate.return_value = Result.Ok(b'fake pdf content')

    mock_email_sender = mocker.MagicMock(spec=AbsEmailSender)
    mock_email_sender.send_single_mail.return_value = Result.Ok(1)

    mocker.patch(
        'payments.infra.tasks.get_pdf_generator',
        return_value=mock_pdf_generator,
    )
    mocker.patch(
        'payments.infra.tasks.get_email_sender',
        return_value=mock_email_sender,
    )
    mocker.patch(
        'payments.infra.tasks.get_payment_repository',
        return_value=MagicMock(get_by_id=MagicMock(return_value=Result.Ok(payment_entity))),
    )

    # Act
    result = tasks.send_payment_confirmation(payment_model.pk)

    # Assert
    assert result.is_ok()
    mock_pdf_generator.generate.assert_called_once_with(payment_entity)
    mock_email_sender.send_single_mail.assert_called_once()
