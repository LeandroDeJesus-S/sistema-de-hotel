import pytest
from exc import Result

from payments.application.usecases import SendPaymentConfirmationUseCase


class TestSendPaymentConfirmationUseCase:
    def test_successful_send_payment_confirmation(
        self, mock_email_sender, mock_pdf_generator, payment_model_instance
    ):
        """Should successfully send payment confirmation email with PDF attachment."""
        # Arrange
        pdf_bytes = b'fake_pdf_data'
        mock_pdf_generator.generate.return_value = Result.Ok(pdf_bytes)
        mock_email_sender.send_single_mail.return_value = Result.Ok(True)

        usecase = SendPaymentConfirmationUseCase(
            mailer=mock_email_sender, pdf_generator=mock_pdf_generator
        )

        # Act
        result = usecase(payment_model_instance)

        # Assert
        assert result.is_ok()
        mock_pdf_generator.generate.assert_called_once_with(payment_model_instance)
        mock_email_sender.send_single_mail.assert_called_once()
        call_args = mock_email_sender.send_single_mail.call_args[1]
        assert call_args['subject'] == 'Reservation payment receipt'
        assert call_args['is_html'] is True
        assert len(call_args['attachments']) == 1
        assert call_args['attachments'][0][0] == 'Payment receipt.pdf'
        assert call_args['attachments'][0][1] == pdf_bytes

    def test_send_fails_when_pdf_generation_fails(
        self, mock_email_sender, mock_pdf_generator, payment_model_instance
    ):
        """Should return error when PDF generation fails."""
        # Arrange
        mock_pdf_generator.generate.return_value = Result.Err('PDF generation failed')

        usecase = SendPaymentConfirmationUseCase(
            mailer=mock_email_sender, pdf_generator=mock_pdf_generator
        )

        # Act
        result = usecase(payment_model_instance)

        # Assert
        assert result.is_err()
        assert 'Failed to generate PDF' in result.unwrap_err().msg
        mock_pdf_generator.generate.assert_called_once_with(payment_model_instance)
        mock_email_sender.send_single_mail.assert_not_called()

    def test_send_fails_when_email_send_fails(
        self, mock_email_sender, mock_pdf_generator, payment_model_instance
    ):
        """Should return error when email sending fails."""
        # Arrange
        pdf_bytes = b'fake_pdf_data'
        mock_pdf_generator.generate.return_value = Result.Ok(pdf_bytes)
        mock_email_sender.send_single_mail.return_value = Result.Err('Email send failed')

        usecase = SendPaymentConfirmationUseCase(
            mailer=mock_email_sender, pdf_generator=mock_pdf_generator
        )

        # Act
        result = usecase(payment_model_instance)

        # Assert
        assert result.is_err()
        assert 'Failed to send email' in result.unwrap_err().msg
        mock_pdf_generator.generate.assert_called_once_with(payment_model_instance)
        mock_email_sender.send_single_mail.assert_called_once()
