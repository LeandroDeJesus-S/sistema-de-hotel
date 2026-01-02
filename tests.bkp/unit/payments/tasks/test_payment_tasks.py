"""
Tests for the payments tasks.
"""

import pytest

from base.ports.email import AbsEmailSender
from base.ports.pdf import AbsPDFGenerator
from exc import Result
from payments import tasks
from payments.domain.entities import Payment as PaymentEntity
from utils.support import model_to_entity


@pytest.mark.django_db
def test_send_payment_confirmation_sends_email_with_valid_payment_id(
    payment_model, mocker, payments_container
):
    """
    Tests if the task returns True if the email is sent correctly with a valid payment ID.
    """
    # Arrange
    payment_entity = model_to_entity(payment_model, PaymentEntity).unwrap()
    pm_repo_mock = mocker.MagicMock()
    pm_repo_mock.get_by_id.return_value = Result.Ok(payment_entity)

    mock_pdf_generator = mocker.MagicMock(spec=AbsPDFGenerator)
    mock_pdf_generator.generate.return_value = Result.Ok(b'fake pdf content')

    mock_email_sender = mocker.MagicMock(spec=AbsEmailSender)
    mock_email_sender.send_single_mail.return_value = Result.Ok(None)

    # Act
    with (
        payments_container.pdf_generator.override(mock_pdf_generator),
        payments_container.email_sender.override(mock_email_sender),
        payments_container.payment_repo.override(pm_repo_mock),
    ):
        result = tasks.send_payment_confirmation(payment_model.pk)

    # Assert
    assert result.is_ok()
    mock_pdf_generator.generate.assert_called_once_with(payment_entity)
    mock_email_sender.send_single_mail.assert_called_once()
