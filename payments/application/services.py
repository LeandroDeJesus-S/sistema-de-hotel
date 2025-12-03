from http import HTTPStatus
from logging import Logger
from typing import Any

from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.application.dtos import CheckoutUseCaseInputDTO
from payments.domain.dtos import CheckoutResultDTO
from payments.domain.ports import (
    AbsPaymentsRepository,
    AbsSessionBasedPayment,
    PaymentWebhookHandler,
    WebhookPayloadError,
    WebhookSignatureError,
)
from reservations.domain.entities import Reservation
from reservations.domain.repo import AbsReservationRepository

from .usecases import CheckoutUseCase


class WebhookResultDTO:
    def __init__(self, response_code: int, err_msg: str | None = None):
        self.response_code = response_code
        self.err_msg = err_msg


def checkout_presenter(
    o: Result[Reservation],
) -> Result[TemplateRenderResultDTO | RedirectResultDTO]:
    if o.is_err():
        redirect_res: Result[RedirectResultDTO] = RedirectResultDTO.safe_create(
            url='rooms',
            code=302,
        )
        if redirect_res.is_err():
            return Result.Err(
                'Failed to create RedirectResultDTO', src_error=redirect_res.unwrap_err()
            )
        return Result.Ok(redirect_res.unwrap())

    reservation = o.unwrap()
    template_res: Result[TemplateRenderResultDTO] = TemplateRenderResultDTO.safe_create(
        template_name='checkout.html', context={'reservation': reservation}
    )
    if template_res.is_err():
        return Result.Err(
            'Failed to create TemplateRenderResultDTO', src_error=template_res.unwrap_err()
        )
    return Result.Ok(template_res.unwrap())


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
            client_repo=client_repo,
            reservation_repo=reservation_repo,
            payment_repo=payment_repo,
            payment_gateway=payment_gateway,
            uow=uow,
            logger=logger,
        )
        self._wh_handler = wh_handler

    def render_checkout(
        self, reservation_id: int
    ) -> Result[TemplateRenderResultDTO | RedirectResultDTO]:
        reservation_res = self._reservation_repo.find_by_id(reservation_id)
        return checkout_presenter(reservation_res)

    def handle_checkout(
        self, reservation_id: int, client_id: int, success_url: str, cancel_url: str
    ) -> Result[CheckoutResultDTO]:
        dto = CheckoutUseCaseInputDTO.safe_create(
            client_id=client_id,
            reservation_id=reservation_id,
            success_url=success_url,
            cancel_url=cancel_url,
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
