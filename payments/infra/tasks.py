from typing import Literal

from dependency_injector.wiring import Provide, inject
from django.utils import timezone

from base.ports.email import AbsEmailSender
from base.ports.pdf import AbsPDFGenerator
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
def send_payment_confirmation(
    payment_id: int,
    payment_repo: AbsPaymentsRepository = Provide[PaymentsContainer.payment_repo],
    usecase: SendPaymentConfirmationUseCase = Provide[PaymentsContainer.confirmation_usecase],
) -> Result[None]:
    """
    Sends a payment confirmation email to the client.

    This task generates a PDF receipt for the payment and attaches it to the email.

    Args:
        payment_id: The ID of the payment to confirm.
        pdf_generator: Optional. The PDF generator to use. Defaults to
            ReportLabPDFReceiptGenerator.
        email_sender: Optional. The email sender to use. Defaults to DjangoEmailSender.
        payment_repo: Optional. The payment repository to use. Defaults to PaymentRepository.

    Returns:
        A Result indicating success or failure.
    """
    payment_result = payment_repo.get_by_id(payment_id)
    if payment_result.is_err():
        raise Result.Err(f'Payment with id {payment_id} not found.').unwrap_err()

    payment = payment_result.unwrap()
    res = usecase(payment)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)


@inject
def process_refund(
    payment_id: int,
    refund_amount_cents: int,
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
        refund_amount_cents: The refund amount in cents.
        reason: The reason for the refund.
        payment_repo: Optional. The payment repository to use. Defaults to PaymentRepository.

    Returns:
        A Result indicating success or failure.
    """

    # Get payment details
    payment_result = payment_repo.get_by_id(payment_id)
    if payment_result.is_err():
        return Result.Err(f'Payment {payment_id} not found')

    payment = payment_result.unwrap()

    # Check if payment intent ID exists
    if not payment.gateway_payment_intent_id:
        return Result.Err('Payment has no associated payment intent ID')

    # Process refund through Stripe
    refund_result = stripe_adapter.process_refund(
        payment.gateway_payment_intent_id, refund_amount_cents, reason
    )

    if refund_result.is_err():
        return Result.Err(
            'Failed to process refund with Stripe', src_error=refund_result.unwrap_err()
        )

    # refund_data = refund_result.unwrap()

    # Update payment record with refund information
    payment.status = PaymentStatus.REFUNDED
    payment.refunded_amount = refund_amount_cents / 100  # Convert cents to dollars
    payment.refunded_at = timezone.now()
    payment.refund_reason = reason

    update_result = payment_repo.update(payment)
    if update_result.is_err():
        return Result.Err(
            'Failed to update payment with refund information',
            src_error=update_result.unwrap_err(),
        )

    return Result.Ok(None)
