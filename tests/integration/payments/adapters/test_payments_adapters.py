import pytest
import json
from unittest.mock import Mock, patch
from django.conf import settings
from exc import Result
from payments.domain.dtos import CheckoutSessionInputDTO, CheckoutItemDTO
from payments.infra.adapters import (
    StripeCheckoutSession,
    StripePaymentWebhookHandler,
    CheckoutSucceededEvent,
    CheckoutExpiredEvent,
    PaymentChargeRefundedEvent,
    WebhookPayloadError,
    WebhookSignatureError
)
from payments.domain.entities import PaymentStatus
from reservations.domain.value_objects import ReservationStatusEnum
from datetime import datetime, timezone, timedelta
import stripe

@pytest.mark.django_db
class TestStripeCheckoutSession:
    @pytest.fixture
    def adapter(self, logger_mock):
        return StripeCheckoutSession(stripe_api_key="sk_test", logger=logger_mock)

    def test_create_checkout_session_success(self, adapter, mocker):
        item = CheckoutItemDTO.safe_create(name="Room", unit_price_cents=10000, quantity=1).unwrap()
        dto = CheckoutSessionInputDTO.safe_create(
            currency="brl",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            success_url="http://success",
            return_url="http://cancel",
            items=[item]
        ).unwrap()

        mock_session = mocker.Mock()
        mock_session.id = "sess_123"
        mock_session.url = "http://stripe.com/sess"
        mock_session.customer = "cus_123"
        mock_session.payment_intent = "pi_123"

        mocker.patch("stripe.checkout.Session.create", return_value=mock_session)

        result = adapter.create_checkout_session(dto)
        assert result.is_ok()
        assert result.unwrap().session_id == "sess_123"

    def test_create_checkout_session_no_items(self, adapter):
        dto = CheckoutSessionInputDTO.safe_create(
            currency="brl",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            success_url="http://success",
            return_url="http://cancel",
            items=[]
        ).unwrap()

        result = adapter.create_checkout_session(dto)
        assert result.is_err()
        assert "No items provided" in result.unwrap_err().msg

    def test_create_checkout_session_failure(self, adapter, mocker):
        item = CheckoutItemDTO.safe_create(name="Room", unit_price_cents=10000, quantity=1).unwrap()
        dto = CheckoutSessionInputDTO.safe_create(
            currency="brl",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            success_url="http://success",
            return_url="http://cancel",
            items=[item]
        ).unwrap()

        mocker.patch("stripe.checkout.Session.create", side_effect=Exception("Stripe error"))

        result = adapter.create_checkout_session(dto)
        assert result.is_err()
        assert "Failed to create Stripe session" in result.unwrap_err().msg

    def test_retrieve_checkout_session_success(self, adapter, mocker):
        mock_session = mocker.Mock()
        mock_session.id = "sess_123"
        mock_session.url = "http://stripe.com/sess"
        mock_session.customer = "cus_123"

        mocker.patch("stripe.checkout.Session.retrieve", return_value=mock_session)

        result = adapter.retrieve_checkout_session("sess_123")
        assert result.is_ok()
        assert result.unwrap().session_id == "sess_123"

    def test_retrieve_checkout_session_failure(self, adapter, mocker):
        mocker.patch("stripe.checkout.Session.retrieve", side_effect=stripe.StripeError("API error"))

        result = adapter.retrieve_checkout_session("sess_123")
        assert result.is_err()
        assert "Failed to retrieve payment session" in result.unwrap_err().msg

    def test_process_refund_success(self, adapter, mocker):
        mock_refund = mocker.Mock()
        mock_refund.id = "re_123"
        mock_refund.amount = 10000
        mock_refund.status = "succeeded"

        mocker.patch("stripe.Refund.create", return_value=mock_refund)

        result = adapter.process_refund("pi_123", 10000)
        assert result.is_ok()
        assert result.unwrap()['refund_id'] == "re_123"

    def test_process_refund_failure(self, adapter, mocker):
        mocker.patch("stripe.Refund.create", side_effect=stripe.StripeError("Refund error"))

        result = adapter.process_refund("pi_123", 10000)
        assert result.is_err()
        assert "Failed to process refund" in result.unwrap_err().msg


class TestStripePaymentWebhookHandler:
    def test_handle_webhook_invalid_payload(self, logger_mock, mocker):
        handler = StripePaymentWebhookHandler(logger=logger_mock)
        # Invalid JSON in request_body
        result = handler.handle_webhook({"request_body": "invalid-json"})
        assert result.is_err()
        assert "invalid payload" in result.unwrap_err().msg

    def test_handle_webhook_invalid_signature(self, logger_mock, mocker, settings):
        settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        handler = StripePaymentWebhookHandler(logger=logger_mock)

        mocker.patch("stripe.Webhook.construct_event", side_effect=stripe.SignatureVerificationError("Invalid sig", "header"))

        result = handler.handle_webhook({
            "request_body": '{"type": "some.event"}',
            "stripe_signature_header": "bad-sig"
        })
        assert result.is_err()
        assert "invalid signature" in result.unwrap_err().msg

    def test_handle_webhook_dispatch_success(self, logger_mock, mocker, settings):
        settings.STRIPE_WEBHOOK_SECRET = None
        handler = StripePaymentWebhookHandler(logger=logger_mock)
        mock_event = mocker.Mock()
        mock_event.ident = "test.event"
        mock_event.handle.return_value = Result.Ok(None)
        handler.with_events(mock_event)

        mock_stripe_event = mocker.Mock()
        mock_stripe_event.type = "test.event"
        mock_stripe_event.data.object = {"id": "obj_123"}
        mocker.patch("stripe.Event.construct_from", return_value=mock_stripe_event)

        result = handler.handle_webhook({"request_body": "{}"})
        assert result.is_ok()
        mock_event.handle.assert_called_once_with({"id": "obj_123"})

    def test_handle_webhook_unknown_event(self, logger_mock, mocker, settings):
        """Should return Ok(None) if event is not registered."""
        settings.STRIPE_WEBHOOK_SECRET = None
        handler = StripePaymentWebhookHandler(logger=logger_mock)

        mock_stripe_event = mocker.Mock()
        mock_stripe_event.type = "unknown.event"
        mocker.patch("stripe.Event.construct_from", return_value=mock_stripe_event)

        result = handler.handle_webhook({"request_body": "{}"})
        assert result.is_ok()

    def test_handle_webhook_event_failure(self, logger_mock, mocker, settings):
        settings.STRIPE_WEBHOOK_SECRET = None
        handler = StripePaymentWebhookHandler(logger=logger_mock)
        mock_event = mocker.Mock()
        mock_event.ident = "test.event"
        mock_event.handle.return_value = Result.Err("Handler error")
        handler.with_events(mock_event)

        mock_stripe_event = mocker.Mock()
        mock_stripe_event.type = "test.event"
        mocker.patch("stripe.Event.construct_from", return_value=mock_stripe_event)

        result = handler.handle_webhook({"request_body": "{}"})
        assert result.is_err()
        assert "Failed to handle webhook event" in result.unwrap_err().msg


@pytest.mark.django_db
class TestWebhookEvents:
    def test_checkout_succeeded_event_handle_success(self, mocker, mock_task_queuer, mock_payments_repository, mock_unit_of_work, logger_mock, reservation_model_instance):
        from payments.infra.adapters import CheckoutSucceededEvent
        from reservations.application.usecases import ActivateReservationUseCase
        from reservations.application.usecases import ScheduleReservationUseCase

        mock_activate = mocker.Mock(spec=ActivateReservationUseCase)
        mock_activate.return_value = Result.Ok(reservation_model_instance)
        mock_schedule = mocker.Mock(spec=ScheduleReservationUseCase)

        event = CheckoutSucceededEvent(
            task_queue=mock_task_queuer,
            payments_repo=mock_payments_repository,
            send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mock_activate,
            release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mock_schedule,
            unit_of_work=mock_unit_of_work,
            logger=logger_mock
        )

        mock_pi = mocker.Mock()
        mock_pi.id = "pi_123"
        mock_pi.latest_charge = "ch_123"
        mock_pi.customer = "cus_123"
        mocker.patch("stripe.PaymentIntent.retrieve", return_value=mock_pi)

        payment = mocker.Mock()
        payment.id = 1
        payment.reservation = reservation_model_instance
        reservation_model_instance.room.available = True
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Ok(None)

        data = {"metadata": {"internal_payment_id": 1}, "payment_intent": "pi_123"}
        result = event.handle(data)

        assert result.is_ok()
        mock_activate.assert_called_once()
        mock_task_queuer.queue_task.assert_called()

    def test_checkout_succeeded_event_handle_schedule_success(self, mocker, mock_task_queuer, mock_payments_repository, mock_unit_of_work, logger_mock, reservation_model_instance):
        from payments.infra.adapters import CheckoutSucceededEvent
        from reservations.application.usecases import ActivateReservationUseCase
        from reservations.application.usecases import ScheduleReservationUseCase

        mock_activate = mocker.Mock(spec=ActivateReservationUseCase)
        mock_schedule = mocker.Mock(spec=ScheduleReservationUseCase)
        mock_schedule.return_value = Result.Ok(reservation_model_instance)

        event = CheckoutSucceededEvent(
            task_queue=mock_task_queuer,
            payments_repo=mock_payments_repository,
            send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mock_activate,
            release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mock_schedule,
            unit_of_work=mock_unit_of_work,
            logger=logger_mock
        )

        mock_pi = mocker.Mock()
        mock_pi.id = "pi_123"
        mock_pi.latest_charge = "ch_123"
        mocker.patch("stripe.PaymentIntent.retrieve", return_value=mock_pi)

        payment = mocker.Mock()
        payment.id = 1
        payment.reservation = reservation_model_instance
        reservation_model_instance.room.available = False # Not available, so schedule
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Ok(None)

        data = {"metadata": {"internal_payment_id": 1}, "payment_intent": "pi_123"}
        result = event.handle(data)

        assert result.is_ok()
        mock_schedule.assert_called_once()
        mock_task_queuer.queue_task.assert_called()

    def test_checkout_succeeded_intent_retrieval_fail(self, mocker, mock_payments_repository, logger_mock):
        from payments.infra.adapters import CheckoutSucceededEvent
        event = CheckoutSucceededEvent(
            task_queue=mocker.Mock(), payments_repo=mock_payments_repository, send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mocker.Mock(), release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mocker.Mock(), unit_of_work=mocker.Mock(), logger=logger_mock
        )
        mocker.patch("stripe.PaymentIntent.retrieve", side_effect=stripe.StripeError("API Error"))

        data = {"payment_intent": "pi_123"}
        result = event.handle(data)

        assert result.is_err()
        assert "Failed to retrieve payment intent" in result.unwrap_err().msg

    def test_checkout_succeeded_no_charge(self, mocker, mock_payments_repository, logger_mock):
        from payments.infra.adapters import CheckoutSucceededEvent
        event = CheckoutSucceededEvent(
            task_queue=mocker.Mock(), payments_repo=mock_payments_repository, send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mocker.Mock(), release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mocker.Mock(), unit_of_work=mocker.Mock(), logger=logger_mock
        )
        mock_pi = mocker.Mock()
        mock_pi.latest_charge = None
        mocker.patch("stripe.PaymentIntent.retrieve", return_value=mock_pi)

        data = {"payment_intent": "pi_123"}
        result = event.handle(data)

        assert result.is_err()
        assert "Payment intent has no charge" in result.unwrap_err().msg

    def test_checkout_succeeded_payment_not_found(self, mocker, mock_payments_repository, mock_unit_of_work, logger_mock):
        from payments.infra.adapters import CheckoutSucceededEvent
        event = CheckoutSucceededEvent(
            task_queue=mocker.Mock(), payments_repo=mock_payments_repository, send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mocker.Mock(), release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mocker.Mock(), unit_of_work=mock_unit_of_work, logger=logger_mock
        )
        mock_pi = mocker.Mock()
        mock_pi.latest_charge = "ch_123"
        mocker.patch("stripe.PaymentIntent.retrieve", return_value=mock_pi)
        mock_payments_repository.get_by_id.return_value = Result.Err("Not found")

        data = {"metadata": {"internal_payment_id": 999}, "payment_intent": "pi_123"}
        result = event.handle(data)

        assert result.is_err()
        assert "Failed to retrieve payment" in result.unwrap_err().msg

    def test_checkout_succeeded_update_failure(self, mocker, mock_payments_repository, mock_unit_of_work, logger_mock, reservation_model_instance):
        from payments.infra.adapters import CheckoutSucceededEvent
        event = CheckoutSucceededEvent(
            task_queue=mocker.Mock(), payments_repo=mock_payments_repository, send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mocker.Mock(), release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mocker.Mock(), unit_of_work=mock_unit_of_work, logger=logger_mock
        )
        mock_pi = mocker.Mock()
        mock_pi.latest_charge = "ch_123"
        mocker.patch("stripe.PaymentIntent.retrieve", return_value=mock_pi)

        payment = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Err("Update failed")

        data = {"metadata": {"internal_payment_id": 1}, "payment_intent": "pi_123"}
        result = event.handle(data)

        assert result.is_err()
        assert "Failed to update payment" in result.unwrap_err().msg
        mock_unit_of_work.rollback.assert_called()

    def test_checkout_succeeded_activation_failure(self, mocker, mock_payments_repository, mock_unit_of_work, logger_mock, reservation_model_instance):
        from payments.infra.adapters import CheckoutSucceededEvent
        from reservations.application.usecases import ActivateReservationUseCase

        mock_activate = mocker.Mock(spec=ActivateReservationUseCase)
        mock_activate.return_value = Result.Err("Activation failed")

        event = CheckoutSucceededEvent(
            task_queue=mocker.Mock(), payments_repo=mock_payments_repository, send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mock_activate, release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mocker.Mock(), unit_of_work=mock_unit_of_work, logger=logger_mock
        )
        mock_pi = mocker.Mock()
        mock_pi.latest_charge = "ch_123"
        mocker.patch("stripe.PaymentIntent.retrieve", return_value=mock_pi)

        payment = mocker.Mock()
        payment.reservation = reservation_model_instance
        reservation_model_instance.room.available = True
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Ok(None)

        data = {"metadata": {"internal_payment_id": 1}, "payment_intent": "pi_123"}
        result = event.handle(data)

        # The code logs error and continues (commits), it does not return Err for activation failure in the current impl
        # based on my read of adapters.py (it commented out return Result.Err)
        # Wait, the code I read:
        # res = self._activate_reservation_usecase(payment.reservation)
        # if res.is_err():
        #     self._logger.error(...)
        #     uow.rollback()
        #     # return Result.Err(...)

        # If it rolls back and returns Ok(None), then test should assert Ok but uow.rollback called.
        assert result.is_ok()
        mock_unit_of_work.rollback.assert_called()

    def test_checkout_succeeded_schedule_failure(self, mocker, mock_payments_repository, mock_unit_of_work, logger_mock, reservation_model_instance):
        from payments.infra.adapters import CheckoutSucceededEvent
        from reservations.application.usecases import ScheduleReservationUseCase

        mock_schedule = mocker.Mock(spec=ScheduleReservationUseCase)
        mock_schedule.return_value = Result.Err("Schedule failed")

        event = CheckoutSucceededEvent(
            task_queue=mocker.Mock(), payments_repo=mock_payments_repository, send_confirmation_task=mocker.Mock(),
            activate_reservation_usecase=mocker.Mock(), release_reservation_task=mocker.Mock(),
            schedule_reservation_usecase=mock_schedule, unit_of_work=mock_unit_of_work, logger=logger_mock
        )
        mock_pi = mocker.Mock()
        mock_pi.latest_charge = "ch_123"
        mocker.patch("stripe.PaymentIntent.retrieve", return_value=mock_pi)

        payment = mocker.Mock()
        payment.reservation = reservation_model_instance
        reservation_model_instance.room.available = False
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Ok(None)

        data = {"metadata": {"internal_payment_id": 1}, "payment_intent": "pi_123"}
        result = event.handle(data)

        # Same as activation, it rolls back and logs error
        assert result.is_ok()
        mock_unit_of_work.rollback.assert_called()

    def test_checkout_expired_event_handle(self, mocker, mock_payments_repository, mock_reservation_repository):
        event = CheckoutExpiredEvent(mock_payments_repository, mock_reservation_repository)

        payment = mocker.Mock()
        payment.reservation = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Ok(None)

        data = {"metadata": {"internal_payment_id": 1}}
        result = event.handle(data)

        assert result.is_ok()
        assert payment.status == PaymentStatus.CANCELLED
        assert payment.reservation.status == ReservationStatusEnum.CANCELLED
        mock_reservation_repository.save.assert_called_once_with(payment.reservation)

    def test_checkout_expired_missing_id(self, mocker, mock_payments_repository, mock_reservation_repository):
        event = CheckoutExpiredEvent(mock_payments_repository, mock_reservation_repository)
        data = {"metadata": {}}
        result = event.handle(data)
        assert result.is_err()
        assert "Payment intent ID not found" in result.unwrap_err().msg

    def test_checkout_expired_payment_not_found(self, mocker, mock_payments_repository, mock_reservation_repository):
        event = CheckoutExpiredEvent(mock_payments_repository, mock_reservation_repository)
        mock_payments_repository.get_by_id.return_value = Result.Err("Not found")
        data = {"metadata": {"internal_payment_id": 1}}
        result = event.handle(data)
        assert result.is_err()
        assert "Failed to retrieve payment" in result.unwrap_err().msg

    def test_checkout_expired_update_fail(self, mocker, mock_payments_repository, mock_reservation_repository):
        event = CheckoutExpiredEvent(mock_payments_repository, mock_reservation_repository)
        payment = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Err("Update failed")
        data = {"metadata": {"internal_payment_id": 1}}
        result = event.handle(data)
        assert result.is_err()
        assert "Failed to update payment" in result.unwrap_err().msg

    def test_payment_charge_refunded_event_handle(self, mocker, mock_payments_repository):
        event = PaymentChargeRefundedEvent(mock_payments_repository)

        payment = mocker.Mock()
        mock_payments_repository.get_by_gateway_payment_intent_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Ok(None)

        data = {"payment_intent": "pi_123"}
        result = event.handle(data)

        assert result.is_ok()
        assert payment.status == PaymentStatus.REFUNDED
        mock_payments_repository.update.assert_called_once_with(payment)

    def test_payment_charge_refunded_missing_id(self, mocker, mock_payments_repository):
        event = PaymentChargeRefundedEvent(mock_payments_repository)
        data = {}
        result = event.handle(data)
        assert result.is_err()
        assert "Payment intent ID not found" in result.unwrap_err().msg

    def test_payment_charge_refunded_not_found(self, mocker, mock_payments_repository):
        event = PaymentChargeRefundedEvent(mock_payments_repository)
        mock_payments_repository.get_by_gateway_payment_intent_id.return_value = Result.Err("Not found")
        data = {"payment_intent": "pi_123"}
        result = event.handle(data)
        assert result.is_err()
        assert "Failed to retrieve payment" in result.unwrap_err().msg

    def test_payment_charge_refunded_update_fail(self, mocker, mock_payments_repository):
        event = PaymentChargeRefundedEvent(mock_payments_repository)
        payment = mocker.Mock()
        mock_payments_repository.get_by_gateway_payment_intent_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Err("Update failed")
        data = {"payment_intent": "pi_123"}
        result = event.handle(data)
        assert result.is_err()
        assert "Failed to update payment" in result.unwrap_err().msg
