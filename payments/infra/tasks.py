from typing import Literal

from dependency_injector.wiring import Provide, inject
from django.utils import timezone

from base.ports.email import AbsEmailSender
from base.ports.pdf import AbsPDFGenerator
from base.ports.queue import TaskQueuer
from exc import Result
from payments.application.usecases import SendPaymentConfirmationUseCase
from payments.container import PaymentsContainer
from payments.domain.entities import PaymentStatus
from payments.domain.ports import AbsPaymentsRepository, AbsSessionBasedPayment
from payments.infra.repo import PaymentRepository
from utils.adapters.email import DjangoEmailSender
from utils.adapters.pdf import ReportLabPDFReceiptGenerator


def get_payment_repository() -> AbsPaymentsRepository:
    return PaymentRepository()


def get_pdf_generator() -> AbsPDFGenerator:
    return ReportLabPDFReceiptGenerator()


def get_email_sender() -> AbsEmailSender:
    return DjangoEmailSender()


@inject
def send_payment_confirmation_email_task(
    payment_id: int,
    payment_repo: AbsPaymentsRepository = Provide[PaymentsContainer.payment_repo],
    usecase: SendPaymentConfirmationUseCase = Provide[PaymentsContainer.confirmation_usecase],
) -> None:
    """
    Send payment confirmation email with PDF receipt.
    """
    try:
        payment_result = payment_repo.get_by_id(payment_id)
        if payment_result.is_err():
            raise Result.Err(f'Payment with id {payment_id} not found.').unwrap_err()

        payment = payment_result.unwrap()
        res = usecase(payment)
        if res.is_err():
            raise Result.Err(
                res.unwrap_err().msg, src_error=res.unwrap_err().src_error
            ).unwrap_err()
    except Exception as e:
        raise Result.Err('Failed to send payment confirmation email', src_error=e).unwrap_err()


@inject
def send_payment_confirmation(
    payment_id: int,
    payment_repo: AbsPaymentsRepository = Provide[PaymentsContainer.payment_repo],
    task_queuer: TaskQueuer = Provide[PaymentsContainer.task_queuer],
) -> Result[None]:
    """
    Queue payment confirmation email task.

    Args:
        payment_id: The ID of the payment to confirm.

    Returns:
        A Result indicating success or failure.
    """
    # Validate payment exists before queuing
    payment_result = payment_repo.get_by_id(payment_id)
    if payment_result.is_err():
        raise Result.Err(f'Payment with id {payment_id} not found.').unwrap_err()

    task_queuer.queue_task(
        send_payment_confirmation_email_task,
        (payment_id,),
        name=f'send_payment_confirmation_{payment_id}',
    )
    return Result.Ok(None)


@inject
def process_refund(
    payment_id: int,
    refund_price_cents: int,
    reason: Literal[
        'duplicate', 'fraudulent', 'requested_by_customer'
    ] = 'requested_by_customer',
    payment_repo: AbsPaymentsRepository = Provide[PaymentsContainer.payment_repo],
    stripe_adapter: AbsSessionBasedPayment = Provide[PaymentsContainer.payment_gateway],
) -> Result[None]:
    """
    Process a refund for a payment.

    Args:
        payment_id: The ID of the payment to refund.
        refund_price_cents: The refund price in cents.
        reason: The reason for the refund.
        payment_repo: Optional. The payment repository to use. Defaults to PaymentRepository.

    Returns:
        A Result indicating success or failure.
    """

    # Get payment details
    payment_result = payment_repo.get_by_id(payment_id)
    if payment_result.is_err():
        raise Result.Err(f'Payment {payment_id} not found').unwrap_err()

    payment = payment_result.unwrap()

    # Check if payment intent ID exists
    if not payment.gateway_payment_intent_id:
        raise Result.Err('Payment has no associated payment intent ID').unwrap_err()

    # Process refund through Stripe
    refund_result = stripe_adapter.process_refund(
        payment.gateway_payment_intent_id, refund_price_cents, reason
    )

    if refund_result.is_err():
        raise Result.Err(
            'Failed to process refund with Stripe', src_error=refund_result.unwrap_err()
        ).unwrap_err()

    # refund_data = refund_result.unwrap()

    # Update payment record with refund information
    payment.status = PaymentStatus.REFUNDED
    payment.refunded_currency = payment.currency
    payment.refunded_price = refund_price_cents
    payment.refunded_at = timezone.now()
    payment.refund_reason = reason

    update_result = payment_repo.update(payment)
    if update_result.is_err():
        raise Result.Err(
            'Failed to update payment with refund information',
            src_error=update_result.unwrap_err(),
        ).unwrap_err()

    return Result.Ok(None)
