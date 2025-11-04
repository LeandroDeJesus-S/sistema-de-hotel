from datetime import timedelta
from logging import Logger

from django.utils.timezone import timezone

from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.application.dtos import CheckoutResultDTO, CheckoutUseCaseInputDTO
from payments.domain.dtos import CheckoutItemDTO, CheckoutSessionInputDTO
from payments.domain.entities import Payment
from payments.domain.ports import (
    AbsPaymentsRepository,
    AbsSessionBasedPayment,
)
from payments.rules import PaymentRules
from reservations.domain.repo import AbsReservationRepository

from .usecases import CheckoutUseCase


class PaymentService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        payment_gateway: AbsSessionBasedPayment,
        payment_repo: AbsPaymentsRepository,
        uow: AbsUnitOfWork,
        logger: Logger,
        reservation_repo: AbsReservationRepository,
        client_repo: AbsClientRepository,
    ):
        self._payment_gateway = payment_gateway
        self._payment_repo = payment_repo
        self._uow = uow
        self._logger = logger
        self._reservation_repo = reservation_repo
        self._client_repo = client_repo
        self._checkout_usecase = CheckoutUseCase(
            payment_repo=payment_repo,
            payment_gateway=payment_gateway,
            uow=uow,
            logger=logger,
        )

    def start_checkout(
        self, reservation_id: int, client_id: int, success_url: str, cancel_url: str
    ) -> Result[CheckoutResultDTO]:
        client = self._client_repo.get_by_id(client_id)
        if client.is_err():
            return Result.Err(
                'Failed to find client',
                src_error=client.unwrap_err(),
            )

        reservation = self._reservation_repo.find_by_id(reservation_id)
        if reservation.is_err():
            return Result.Err(
                'Failed to find reservation',
                src_error=reservation.unwrap_err(),
            )

        with self._uow as w:
            new_payment = Payment.safe_create(
                client=client.unwrap(),
                reservation=reservation.unwrap(),
                success_url=success_url,
                cancel_url=cancel_url,
            ).then(self._payment_repo.create)

            if new_payment.is_err():
                w.rollback()
                return Result.Err(
                    'Failed to create payment',
                    src_error=new_payment.unwrap_err(),
                )

        reservation_days = reservation.unwrap().reservation_days()
        dto = CheckoutUseCaseInputDTO(
            client=client.unwrap(),
            reservation=reservation.unwrap(),
            checkout_session_input=CheckoutSessionInputDTO(
                currency='brl',
                expires_at=timezone.now()
                + timedelta(minutes=PaymentRules.CHECKOUT_SESSION_EXPIRES_MIN),
                success_url=success_url,
                return_url=cancel_url,
                items=[
                    CheckoutItemDTO(
                        name=(
                            f'Reserva: Quarto Nº{reservation.unwrap().room.number}, '
                            f'classe {reservation.unwrap().room.room_class}.'
                        ),
                        unit_price_cents=int(reservation.unwrap().room.daily_price * 100),
                        quantity=reservation_days,
                    )
                ],
            ),
        )
        return self._checkout_usecase(dto).map(
            lambda res: CheckoutResultDTO(redirect_url=res.session_url)
        )
