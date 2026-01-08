import pytest
from unittest.mock import Mock
from exc import Result, Error
from payments.infra.tasks import (
    send_payment_confirmation,
    process_refund,
    send_payment_confirmation_email_task,
    get_payment_repository,
    get_pdf_generator,
    get_email_sender,
)
from payments.domain.entities import PaymentStatus


def test_getters():
    assert get_payment_repository() is not None
    assert get_pdf_generator() is not None
    assert get_email_sender() is not None


@pytest.mark.django_db
class TestSendPaymentConfirmationTask:
    def test_send_payment_confirmation_success(
        self, mocker, mock_payments_repository, mock_task_queuer, payments_container
    ):
        payment = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.task_queuer.override(mock_task_queuer),
        ):
            result = send_payment_confirmation(payment_id=1)
            assert result.is_ok()
            mock_task_queuer.queue_task.assert_called_once_with(
                send_payment_confirmation_email_task, (1,), name='send_payment_confirmation_1'
            )

    def test_send_payment_confirmation_not_found(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_payments_repository.get_by_id.return_value = Result.Err('Not found')

        with payments_container.payment_repo.override(mock_payments_repository):
            with pytest.raises(Error) as exc:
                send_payment_confirmation(payment_id=1)
            assert 'not found' in str(exc.value)

    def test_send_payment_confirmation_usecase_error(
        self, mocker, mock_payments_repository, mock_task_queuer, payments_container
    ):
        payment = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.task_queuer.override(mock_task_queuer),
        ):
            result = send_payment_confirmation(payment_id=1)
            assert result.is_ok()
            # Usecase errors are handled in separate tasks, so main task succeeds
            assert mock_task_queuer.queue_task.call_count == 1

    def test_send_payment_confirmation_email_task_success(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Ok(None)

        payment = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.confirmation_usecase.override(mock_usecase),
        ):
            # Should not raise any exception
            send_payment_confirmation_email_task(payment_id=1)
            mock_usecase.assert_called_once_with(payment)

    def test_send_payment_confirmation_email_task_payment_not_found(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_payments_repository.get_by_id.return_value = Result.Err('Not found')

        with payments_container.payment_repo.override(mock_payments_repository):
            with pytest.raises(Error) as exc:
                send_payment_confirmation_email_task(payment_id=1)
            assert 'not found' in str(exc.value)

    def test_send_payment_confirmation_email_task_usecase_error(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.return_value = Result.Err('Usecase failed')

        payment = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.confirmation_usecase.override(mock_usecase),
        ):
            with pytest.raises(Error) as exc:
                send_payment_confirmation_email_task(payment_id=1)
            assert 'Usecase failed' in str(exc.value)

    def test_send_payment_confirmation_email_task_general_exception(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.side_effect = Exception('Unexpected error')

        payment = mocker.Mock()
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.confirmation_usecase.override(mock_usecase),
        ):
            with pytest.raises(Error) as exc:
                send_payment_confirmation_email_task(payment_id=1)
            assert 'Failed to send payment confirmation email' in str(exc.value)


@pytest.mark.django_db
class TestProcessRefundTask:
    def test_process_refund_success(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_stripe = mocker.Mock()
        mock_stripe.process_refund.return_value = Result.Ok({})

        payment = mocker.Mock()
        payment.gateway_payment_intent_id = 'pi_123'
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Ok(None)

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.payment_gateway.override(mock_stripe),
        ):
            result = process_refund(payment_id=1, refund_amount_cents=1000)
            assert result.is_ok()
            assert payment.status == PaymentStatus.REFUNDED
            mock_stripe.process_refund.assert_called_once_with(
                'pi_123', 1000, 'requested_by_customer'
            )

    def test_process_refund_payment_not_found(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_payments_repository.get_by_id.return_value = Result.Err('Not found')

        with payments_container.payment_repo.override(mock_payments_repository):
            with pytest.raises(Error) as exc:
                process_refund(payment_id=1, refund_amount_cents=1000)
            assert 'not found' in str(exc.value)

    def test_process_refund_no_pi_id(
        self, mocker, mock_payments_repository, payments_container
    ):
        payment = mocker.Mock()
        payment.gateway_payment_intent_id = None
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)

        with payments_container.payment_repo.override(mock_payments_repository):
            with pytest.raises(Error) as exc:
                process_refund(payment_id=1, refund_amount_cents=1000)
            assert 'no associated payment intent ID' in str(exc.value)

    def test_process_refund_stripe_error(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_stripe = mocker.Mock()
        mock_stripe.process_refund.return_value = Result.Err('Stripe error')

        payment = mocker.Mock()
        payment.gateway_payment_intent_id = 'pi_123'
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.payment_gateway.override(mock_stripe),
        ):
            with pytest.raises(Error) as exc:
                process_refund(payment_id=1, refund_amount_cents=1000)
            assert 'Failed to process refund with Stripe' in str(exc.value)

    def test_process_refund_update_error(
        self, mocker, mock_payments_repository, payments_container
    ):
        mock_stripe = mocker.Mock()
        mock_stripe.process_refund.return_value = Result.Ok({})

        payment = mocker.Mock()
        payment.gateway_payment_intent_id = 'pi_123'
        mock_payments_repository.get_by_id.return_value = Result.Ok(payment)
        mock_payments_repository.update.return_value = Result.Err('Update error')

        with (
            payments_container.payment_repo.override(mock_payments_repository),
            payments_container.payment_gateway.override(mock_stripe),
        ):
            with pytest.raises(Error) as exc:
                process_refund(payment_id=1, refund_amount_cents=1000)
            assert 'Failed to update payment' in str(exc.value)
