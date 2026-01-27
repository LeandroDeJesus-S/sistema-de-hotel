import logging
from datetime import datetime, timedelta

from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as gtl

from base.ports.pdf import AbsPDFGenerator
from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.application.dtos import CheckoutUseCaseInputDTO
from payments.domain.dtos import CheckoutItemDTO, CheckoutResultDTO, CheckoutSessionInputDTO
from payments.rules import PaymentRules
from reservations.domain.repo import AbsReservationRepository
from utils.adapters.email import AbsEmailSender

from ..domain.entities import Payment, PaymentGateway, PaymentStatus
from ..domain.ports import AbsPaymentsRepository, AbsSessionBasedPayment


class CheckoutUseCase:
    """
    Use case for handling the checkout process.

    This use case orchestrates the creation of a payment session and a payment record.
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        client_repo: AbsClientRepository,
        payment_repo: AbsPaymentsRepository,
        payment_gateway: AbsSessionBasedPayment,
        reservation_repo: AbsReservationRepository,
        uow: AbsUnitOfWork,
        logger: logging.Logger,
    ):
        self._client_repo = client_repo
        self._payment_repo = payment_repo
        self._payment_gateway = payment_gateway
        self._reservation_repo = reservation_repo
        self._uow = uow
        self._logger = logger

    def __call__(self, dto: CheckoutUseCaseInputDTO) -> Result[CheckoutResultDTO]:  # noqa: PLR0911
        """
        Executes the checkout use case.

        Args:
            dto: The data transfer object containing the checkout information.

        Returns:
            A Result containing the checkout result DTO on success, or an Error on failure.
        """

        with self._uow as w:
            payment = self._payment_repo.get_pending_from(dto.reservation_id).unwrap_or(None)
            if not payment:  # we create a new payment record and a new session
                assert dto.client_id is not None  # nosec
                client = self._client_repo.get_by_id(dto.client_id)
                if client.is_err():
                    return Result.Err(
                        'Failed to find client',
                        src_error=client.unwrap_err(),
                    )

                reservation_result = self._reservation_repo.find_by_id(dto.reservation_id)
                if reservation_result.is_err():
                    return Result.Err(
                        'Failed to find reservation',
                        src_error=reservation_result.unwrap_err(),
                    )

                reservation = reservation_result.unwrap()
                reservation_days = reservation.reservation_days().unwrap()

                session_input_result = CheckoutSessionInputDTO.safe_create(
                    currency=reservation.currency,
                    expires_at=timezone.now()
                    + timedelta(minutes=PaymentRules.CHECKOUT_SESSION_EXPIRES_MIN),
                    success_url=dto.success_url,
                    return_url=dto.cancel_url,
                    items=[
                        CheckoutItemDTO.safe_create(
                            name=gtl('Reservation: Room No. %(number)s, class %(class)s.')
                            % {
                                'number': reservation.room.number,
                                'class': reservation.room.room_class.name,
                            },
                            unit_price_cents=int(reservation.price / reservation_days),
                            quantity=reservation_days,
                        ).unwrap()
                    ],
                )
                if session_input_result.is_err():
                    return Result.Err(
                        'Failed to create checkout session input',
                        src_error=session_input_result.unwrap_err(),
                    )
                session = session_input_result.unwrap()

                assert dto.reservation_id is not None  # nosec
                new_payment_result = Payment.safe_create(
                    client=client.unwrap(),
                    reservation=reservation,
                    currency=reservation.currency,
                    price=reservation.price,
                    status=PaymentStatus.PENDING,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    payment_gateway=PaymentGateway.STRIPE,
                ).then(self._payment_repo.create)

                if new_payment_result.is_err():
                    self._logger.error(
                        'Failed to create payment', exc_info=new_payment_result.unwrap_err()
                    )
                    w.rollback()
                    return Result.Err(
                        'Failed to create payment',
                        src_error=new_payment_result.unwrap_err(),
                    )

                new_payment = new_payment_result.unwrap()

                metadata = session.metadata or {}
                metadata['internal_payment_id'] = new_payment.id
                session.metadata = metadata

                session_result = self._payment_gateway.create_checkout_session(session)
                if session_result.is_err():
                    self._logger.error(
                        'Failed to create payment session',
                        exc_info=session_result.unwrap_err(),
                    )
                    w.rollback()
                    return Result.Err(
                        'Failed to create payment session',
                        src_error=session_result.unwrap_err(),
                    )
                new_payment.gateway_payment_session_id = session_result.unwrap().session_id
                res = self._payment_repo.update(new_payment)
                if res.is_err():
                    self._logger.error('Failed to create payment', exc_info=res.unwrap_err())
                    w.rollback()
                    return Result.Err(
                        'Failed to create payment',
                        src_error=res.unwrap_err(),
                    )
                w.commit()
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
        pdf_bytes = self._pdf_generator.generate(payment, payment.reservation.client.language)
        if pdf_bytes.is_err():
            return Result.Err(
                'Failed to generate PDF',
                src_error=pdf_bytes.unwrap_err(),
            )

        html_body = render_to_string('emails/payment_confirmation.html', {'payment': payment})
        sent = self._mailer.send_single_mail(
            subject=gtl('Reservation payment receipt'),
            body=html_body,
            from_email=None,
            to_emails=[payment.reservation.client.email],
            is_html=True,
            attachments=(
                (
                    gtl('Payment receipt.pdf'),
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
