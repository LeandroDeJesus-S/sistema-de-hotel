import logging
from datetime import datetime, timezone

from base.ports.pdf import AbsPDFGenerator
from base.ports.unit_of_work import AbsUnitOfWork
from exc import Result
from utils.adapters.email import AbsEmailSender

from ..domain.dtos import CheckoutResultDTO
from ..domain.entities import Payment, PaymentGateway, PaymentStatus
from ..domain.ports import AbsPaymentsRepository, AbsSessionBasedPayment
from .dtos import CheckoutUseCaseInputDTO


class CheckoutUseCase:
    """
    Use case for handling the checkout process.

    This use case orchestrates the creation of a payment session and a payment record.
    """

    def __init__(
        self,
        payment_repo: AbsPaymentsRepository,
        payment_gateway: AbsSessionBasedPayment,
        uow: AbsUnitOfWork,
        logger: logging.Logger,
    ):
        self._payment_repo = payment_repo
        self._payment_gateway = payment_gateway
        self._uow = uow
        self._logger = logger

    def __call__(self, dto: CheckoutUseCaseInputDTO) -> Result[CheckoutResultDTO]:
        """
        Executes the checkout use case.

        Args:
            dto: The data transfer object containing the checkout information.

        Returns:
            A Result containing the checkout result DTO on success, or an Error on failure.
        """
        with self._uow as w:
            payment = dto.pending_payment
            if payment is None and dto.checkout_session_input is not None:
                assert dto.reservation is not None  # nosec
                new_payment = Payment.safe_create(
                    client=dto.client,
                    reservation=dto.reservation,
                    amount=dto.reservation.amount,
                    status=PaymentStatus.PENDING,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    payment_gateway=PaymentGateway.STRIPE,
                ).then(self._payment_repo.create)

                if new_payment.is_err():
                    self._logger.error(
                        'Failed to create payment', exc_info=new_payment.unwrap_err()
                    )
                    w.rollback()
                    return Result.Err(
                        'Failed to create payment',
                        src_error=new_payment.unwrap_err(),
                    )

                payment = new_payment.unwrap()

                metadata = dto.checkout_session_input.metadata or {}
                metadata['internal_payment_id'] = payment.id
                dto.checkout_session_input.metadata = metadata

                session_result = self._payment_gateway.create_checkout_session(
                    dto.checkout_session_input
                )
                if session_result.is_err():
                    self._logger.error('Failed to create payment session')
                    # w.rollback() WARN: be sure that there are no db operations in `create_checkout_session`  # noqa: E501
                    return Result.Err(
                        'Failed to create payment session',
                        src_error=session_result.unwrap_err(),
                    )
                payment.gateway_payment_session_id = session_result.unwrap().session_id
                self._payment_repo.update(payment).match(
                    on_ok=lambda _: w.commit(), on_err=lambda _: w.rollback()
                )
                return session_result

        if not payment or not payment.gateway_payment_session_id:
            return Result.Err('Payment is None or payment session ID not found')

        return self._payment_gateway.retrieve_checkout_session(
            payment.gateway_payment_session_id
        )


class SendPaymentConfirmationUseCase:
    """Use case for sending a payment confirmation email. It generates a PDF document and sends
    it to the client's email."""

    def __init__(
        self,
        mailer: AbsEmailSender,
        pdf_generator: AbsPDFGenerator,
    ):
        self._mailer = mailer
        self._pdf_generator = pdf_generator

    def __call__(self, payment: Payment) -> Result[None]:
        pdf_bytes = self._pdf_generator.generate(payment)
        if pdf_bytes.is_err():
            return Result.Err(
                'Failed to generate PDF',
                src_error=pdf_bytes.unwrap_err(),
            )

        sent = self._mailer.send_single_mail(
            subject='Comprovante de pagamento  da reserva',
            body=(
                'Seu comprovante de pagamento para a reserva do '
                f'quarto Nº{payment.reservation.room.number}'
            ),
            from_email=None,
            to_emails=[payment.reservation.client.email],
            attachments=(
                (
                    'Comprovante de pagamento.pdf',
                    pdf_bytes.unwrap(),
                    'application/pdf',
                ),
            ),
        )
        if sent.is_err():
            return Result.Err(
                'Failed to send email',
                src_error=sent.unwrap_err(),
            )
        return Result.Ok(None)
