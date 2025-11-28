from datetime import timedelta
from http import HTTPStatus
from logging import Logger
from typing import Any

from django.utils import timezone

from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.application.dtos import CheckoutUseCaseInputDTO
from payments.domain.dtos import CheckoutItemDTO, CheckoutResultDTO, CheckoutSessionInputDTO
from payments.domain.entities import PaymentStatus
from payments.domain.ports import (
    AbsPaymentsRepository,
    AbsSessionBasedPayment,
    PaymentWebhookHandler,
    WebhookPayloadError,
    WebhookSignatureError,
)
from payments.rules import PaymentRules
from reservations.domain.repo import AbsReservationRepository

from .usecases import CheckoutUseCase


class WebhookResultDTO:
    def __init__(self, response_code: int, err_msg: str | None = None):
        self.response_code = response_code
        self.err_msg = err_msg


class PaymentService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        payment_gateway: AbsSessionBasedPayment,
        payment_repo: AbsPaymentsRepository,
        uow: AbsUnitOfWork,
        logger: Logger,
        reservation_repo: AbsReservationRepository,
        client_repo: AbsClientRepository,
        wh_handler: PaymentWebhookHandler,
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
        self._wh_handler = wh_handler

    def start_checkout(
        self, reservation_id: int, client_id: int, success_url: str, cancel_url: str
    ) -> Result[CheckoutResultDTO]:
        payment = self._payment_repo.get_by_reservation_id(reservation_id).unwrap_or(None)
        if payment and payment.status == PaymentStatus.PENDING:
            dto = CheckoutUseCaseInputDTO.safe_create(
                pending_payment=payment,
            )
            if dto.is_err():
                return Result.Err(
                    'Failed to create checkout session input',
                    src_error=dto.unwrap_err(),
                )
            return self._checkout_usecase(dto.unwrap())

        client = self._client_repo.get_by_id(client_id)
        if client.is_err():
            return Result.Err(
                'Failed to find client',
                src_error=client.unwrap_err(),
            )

        reservation_result = self._reservation_repo.find_by_id(reservation_id)
        if reservation_result.is_err():
            return Result.Err(
                'Failed to find reservation',
                src_error=reservation_result.unwrap_err(),
            )

        reservation = reservation_result.unwrap()
        reservation_days = reservation.reservation_days().unwrap()

        session_result = CheckoutSessionInputDTO.safe_create(
            currency='brl',  # TODO: make it dynamic
            expires_at=timezone.now()
            + timedelta(minutes=PaymentRules.CHECKOUT_SESSION_EXPIRES_MIN),
            success_url=success_url,
            return_url=cancel_url,
            items=[
                CheckoutItemDTO.safe_create(
                    name=(
                        f'Reserva: Quarto Nº{reservation.room.number}, '
                        f'classe {reservation.room.room_class.name}.'
                    ),
                    unit_price_cents=int(reservation.room.daily_price * 100),
                    quantity=reservation_days,
                ).unwrap()
            ],
        )
        dto = CheckoutUseCaseInputDTO.safe_create(
            client=client.unwrap(),
            reservation=reservation,
            checkout_session_input=session_result.unwrap(),
        )
        if dto.is_err():
            return Result.Err(
                'Failed to create checkout session input',
                src_error=dto.unwrap_err(),
            )
        return self._checkout_usecase(dto.unwrap())

    def handle_webhook(self, data: dict[str, Any], *target_events) -> Result[WebhookResultDTO]:
        """Handles a webhook event dispatching by its identifier. It never returns an error.

        Args:
            data: The webhook data.
            *target_events: The events to be handled.

        Returns:
            A Result containing the response code on success, if a error occurred, the error
            message will be passed through the WebhookResultDTO.
        """
        self._wh_handler.with_events(*target_events)
        result = self._wh_handler.handle_webhook(data)

        if result.is_ok():
            return Result.Ok(WebhookResultDTO(response_code=HTTPStatus.OK))

        err = result.unwrap_err()
        if isinstance(err.src_error, WebhookPayloadError):
            return Result.Ok(
                WebhookResultDTO(
                    response_code=HTTPStatus.BAD_REQUEST, err_msg='Invalid payload'
                )
            )

        if isinstance(err.src_error, WebhookSignatureError):
            return Result.Ok(
                WebhookResultDTO(
                    response_code=HTTPStatus.UNAUTHORIZED, err_msg='Invalid signature'
                )
            )

        return Result.Ok(WebhookResultDTO(response_code=HTTPStatus.OK))
