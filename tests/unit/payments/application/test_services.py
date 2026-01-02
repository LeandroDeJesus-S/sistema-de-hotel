import pytest
from http import HTTPStatus
from exc import Result

from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from payments.application.services import PaymentService, WebhookResultDTO
from payments.domain.dtos import CheckoutResultDTO
from payments.domain.ports import WebhookPayloadError, WebhookSignatureError


class TestPaymentService:
    def test_render_checkout_success(
        self,
        mock_reservation_repository,
        reservation_model_instance,
    ):
        """Should render checkout template when reservation exists."""
        # Arrange
        mock_reservation_repository.find_by_id.return_value = Result.Ok(
            reservation_model_instance
        )
        service = PaymentService(
            payment_gateway=None,  # Not used in this method
            payment_repo=None,
            uow=None,
            logger=None,
            reservation_repo=mock_reservation_repository,
            client_repo=None,
            wh_handler=None,
        )

        # Act
        result = service.render_checkout(reservation_model_instance.id)

        # Assert
        assert isinstance(result, Result)
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'checkout.html'
        assert 'reservation' in dto.context
        mock_reservation_repository.find_by_id.assert_called_once_with(
            reservation_model_instance.id
        )

    def test_render_checkout_reservation_not_found(
        self,
        mock_reservation_repository,
    ):
        """Should return redirect when reservation not found."""
        # Arrange
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')
        service = PaymentService(
            payment_gateway=None,
            payment_repo=None,
            uow=None,
            logger=None,
            reservation_repo=mock_reservation_repository,
            client_repo=None,
            wh_handler=None,
        )

        # Act
        result = service.render_checkout(999)

        # Assert
        assert isinstance(result, Result)
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'rooms'
        assert dto.code == 302

    def test_handle_checkout_success(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        client_model_instance,
        reservation_model_instance,
    ):
        """Should successfully handle checkout by calling usecase."""
        # Arrange
        checkout_result = CheckoutResultDTO.safe_create(
            client_id='client_123', session_id='session_123', session_url='http://checkout.com'
        ).unwrap()
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(checkout_result)
        mocker.patch(
            'payments.application.services.CheckoutUseCase', return_value=mock_usecase
        )

        service = PaymentService(
            payment_gateway=mock_session_based_payment,
            payment_repo=mock_payments_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
            reservation_repo=mock_reservation_repository,
            client_repo=mock_client_repository,
            wh_handler=None,
        )

        # Act
        result = service.handle_checkout(
            reservation_id=reservation_model_instance.id,
            client_id=client_model_instance.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )

        # Assert
        assert result.is_ok()
        assert result.unwrap().session_id == 'session_123'
        mock_usecase.assert_called_once()

    def test_handle_webhook_success(
        self,
        mock_payment_webhook_handler,
    ):
        """Should handle webhook successfully."""
        # Arrange
        mock_payment_webhook_handler.with_events.return_value = Result.Ok(None)
        mock_payment_webhook_handler.handle_webhook.return_value = Result.Ok(None)
        service = PaymentService(
            payment_gateway=None,
            payment_repo=None,
            uow=None,
            logger=None,
            reservation_repo=None,
            client_repo=None,
            wh_handler=mock_payment_webhook_handler,
        )

        # Act
        result = service.handle_webhook({'event': 'test'})

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert dto.response_code == HTTPStatus.OK
        assert dto.err_msg is None
        mock_payment_webhook_handler.with_events.assert_called_once()
        mock_payment_webhook_handler.handle_webhook.assert_called_once_with({'event': 'test'})

    def test_handle_webhook_payload_error(
        self,
        mock_payment_webhook_handler,
    ):
        """Should return BAD_REQUEST for payload error."""
        # Arrange
        mock_payment_webhook_handler.with_events.return_value = Result.Ok(None)
        error = WebhookPayloadError()
        mock_payment_webhook_handler.handle_webhook.return_value = Result.Err(
            'Error', src_error=error
        )
        service = PaymentService(
            payment_gateway=None,
            payment_repo=None,
            uow=None,
            logger=None,
            reservation_repo=None,
            client_repo=None,
            wh_handler=mock_payment_webhook_handler,
        )

        # Act
        result = service.handle_webhook({'event': 'test'})

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert dto.response_code == HTTPStatus.BAD_REQUEST
        assert dto.err_msg == 'Invalid payload'

    def test_handle_webhook_signature_error(
        self,
        mock_payment_webhook_handler,
    ):
        """Should return UNAUTHORIZED for signature error."""
        # Arrange
        mock_payment_webhook_handler.with_events.return_value = Result.Ok(None)
        error = WebhookSignatureError()
        mock_payment_webhook_handler.handle_webhook.return_value = Result.Err(
            'Error', src_error=error
        )
        service = PaymentService(
            payment_gateway=None,
            payment_repo=None,
            uow=None,
            logger=None,
            reservation_repo=None,
            client_repo=None,
            wh_handler=mock_payment_webhook_handler,
        )

        # Act
        result = service.handle_webhook({'event': 'test'})

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert dto.response_code == HTTPStatus.UNAUTHORIZED
        assert dto.err_msg == 'Invalid signature'

    def test_handle_webhook_other_error(
        self,
        mock_payment_webhook_handler,
    ):
        """Should return OK for other errors."""
        # Arrange
        mock_payment_webhook_handler.with_events.return_value = Result.Ok(None)
        mock_payment_webhook_handler.handle_webhook.return_value = Result.Err('Other error')
        service = PaymentService(
            payment_gateway=None,
            payment_repo=None,
            uow=None,
            logger=None,
            reservation_repo=None,
            client_repo=None,
            wh_handler=mock_payment_webhook_handler,
        )

        # Act
        result = service.handle_webhook({'event': 'test'})

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert dto.response_code == HTTPStatus.OK
        assert dto.err_msg is None

    def test_render_payment_success(
        self,
        mock_payments_repository,
        payment_model_instance,
    ):
        """Should render payment success template when payment exists."""
        # Arrange
        mock_payments_repository.get_by_reservation_id.return_value = Result.Ok(
            payment_model_instance
        )
        service = PaymentService(
            payment_gateway=None,
            payment_repo=mock_payments_repository,
            uow=None,
            logger=None,
            reservation_repo=None,
            client_repo=None,
            wh_handler=None,
        )

        # Act
        result = service.render_payment_success(payment_model_instance.reservation.id)

        # Assert
        assert isinstance(result, Result)
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'success.html'
        assert 'payment' in dto.context
        mock_payments_repository.get_by_reservation_id.assert_called_once_with(
            payment_model_instance.reservation.id
        )

    def test_render_payment_success_payment_not_found(
        self,
        mock_payments_repository,
        logger_mock,
    ):
        """Should return redirect and log error when payment not found."""
        # Arrange
        mock_payments_repository.get_by_reservation_id.return_value = Result.Err('Not found')
        service = PaymentService(
            payment_gateway=None,
            payment_repo=mock_payments_repository,
            uow=None,
            logger=logger_mock,
            reservation_repo=None,
            client_repo=None,
            wh_handler=None,
        )

        # Act
        result = service.render_payment_success(999)

        # Assert
        assert isinstance(result, Result)
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'rooms'
        assert dto.code == 302
        logger_mock.error.assert_called_once()

    def test_render_payment_cancel(
        self,
        mock_reservation_repository,
        reservation_model_instance,
    ):
        """Should render payment cancel template when reservation exists."""
        # Arrange
        mock_reservation_repository.find_by_id.return_value = Result.Ok(
            reservation_model_instance
        )
        service = PaymentService(
            payment_gateway=None,
            payment_repo=None,
            uow=None,
            logger=None,
            reservation_repo=mock_reservation_repository,
            client_repo=None,
            wh_handler=None,
        )

        # Act
        result = service.render_payment_cancel(reservation_model_instance.id)

        # Assert
        assert isinstance(result, Result)
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'cancel.html'
        assert 'reservation' in dto.context
        mock_reservation_repository.find_by_id.assert_called_once_with(
            reservation_model_instance.id
        )

    def test_render_payment_cancel_reservation_not_found(
        self,
        mock_reservation_repository,
        logger_mock,
    ):
        """Should return redirect and log error when reservation not found."""
        # Arrange
        mock_reservation_repository.find_by_id.return_value = Result.Err('Not found')
        service = PaymentService(
            payment_gateway=None,
            payment_repo=None,
            uow=None,
            logger=logger_mock,
            reservation_repo=mock_reservation_repository,
            client_repo=None,
            wh_handler=None,
        )

        # Act
        result = service.render_payment_cancel(999)

        # Assert
        assert isinstance(result, Result)
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'rooms'
        assert dto.code == 302
        logger_mock.error.assert_called_once()
