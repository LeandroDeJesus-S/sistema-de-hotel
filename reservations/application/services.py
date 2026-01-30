import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, Union

from django.conf import settings
from django.utils import timezone

from base.dtos import MessageDTO, RedirectResultDTO, TemplateRenderResultDTO
from base.ports.queue import TaskQueuer
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.domain.ports import AbsPaymentsRepository
from reservations.application.dtos import CreateReservationInput
from reservations.domain.entities import Reservation
from reservations.feedback_messages import ReservationMessages
from utils.adapters.unit_of_work import AbsUnitOfWork

from ..domain.repo import AbsReservationRepository, AbsRoomRepository
from .usecases import (
    CancelReservationUseCase,
    FetchClientActiveReservations,
    FetchClientReservationHistoryUseCase,
    FetchReservationDetailUseCase,
    InitializeReservationUseCase,
)


class ReservationService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        reservation_repo: AbsReservationRepository,
        room_repo: AbsRoomRepository,
        client_repo: AbsClientRepository,
        payments_repo: AbsPaymentsRepository,
        uow: AbsUnitOfWork,
        task_queuer: TaskQueuer,
        logger: logging.Logger,
    ):
        self.reservation_repo = reservation_repo
        self.room_repo = room_repo
        self.client_repo = client_repo
        self.logger = logger

        self._initialize_reservation = InitializeReservationUseCase(
            reservation_repo, room_repo, client_repo, uow, logger=self.logger
        )
        self._fetch_client_active_reservations = FetchClientActiveReservations(
            reservation_repo
        )
        self._fetch_client_reservation_history = FetchClientReservationHistoryUseCase(
            reservation_repo
        )
        self._fetch_reservation_detail = FetchReservationDetailUseCase(reservation_repo)
        self._cancel_reservation = CancelReservationUseCase(
            reservation_repo, room_repo, payments_repo, uow, task_queuer, logger
        )

    def create_reservation(
        self, data: Dict[str, Any]
    ) -> Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]]:
        command = CreateReservationInput.safe_validate(data)
        if command.is_err():
            err = command.unwrap_err()
            self.logger.error(f'invalid reservation data: {err.msg}', exc_info=err.src_error)
            if room_pk := data.get('room_pk'):
                return Result.Ok(
                    RedirectResultDTO(
                        url='reserve',
                        args=(room_pk,),
                        messages=[MessageDTO(typ='error', msg=err.msg)],
                    )
                )
            return Result.Ok(
                RedirectResultDTO(
                    url='rooms',
                    messages=[MessageDTO(typ='error', msg=err.msg)],
                )
            )

        cmd = command.unwrap()
        pending = self.reservation_repo.fetch_pending(
            cmd.client_id, cmd.room_pk, cmd.check_in, cmd.check_out
        ).unwrap_or(None)
        if pending:
            self.logger.info(f'found pending reservation {pending.id}')
            return Result.Ok(RedirectResultDTO(url='checkout', args=(pending.id,)))

        result = self._initialize_reservation(command.unwrap())
        if result.is_err():
            err = result.unwrap_err()
            self.logger.error(
                f'failed to initialize reservation: {err.msg}', exc_info=err.src_error
            )
            return Result.Ok(
                RedirectResultDTO(
                    url='reserve',
                    args=(cmd.room_pk,),
                    messages=[
                        MessageDTO(typ='error', msg=err.msg)
                    ],  # cast to str due it can be a lazy obj
                )
            )

        res = result.unwrap()
        self.logger.info(f'reservation {res.id} registered')
        return Result.Ok(RedirectResultDTO(url='checkout', args=(res.id,)))

    def can_client_create_reservation(
        self, client_id: int
    ) -> Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]]:
        """Check if client can create a new reservation (no active/scheduled ones)."""
        has = self.reservation_repo.has_active_reservation(
            client_id=client_id, include_scheduled=True
        ).unwrap_or(False)

        if has:
            self.logger.info(
                f'client {client_id} already has a reservation active or scheduled'
            )
            return Result.Ok(
                RedirectResultDTO(
                    url='rooms',
                    messages=[
                        MessageDTO(
                            typ='info',
                            msg=str(ReservationMessages.ALREADY_HAVE_A_RESERVATION),
                        )
                    ],
                )
            )

        return Result.Ok(TemplateRenderResultDTO(template_name='reserve.html', context={}))

    def can_cancel_reservation(self, reservation: Reservation) -> Result[bool]:
        """Determine if a specific reservation can be cancelled."""
        now = timezone.now()
        checkin_datetime = datetime.combine(reservation.checkin, time.min, tzinfo=now.tzinfo)
        time_diff = checkin_datetime - now
        return Result.Ok(
            reservation.status in {'A', 'S'}  # ACTIVE or SCHEDULED
            and time_diff >= timedelta(hours=settings.RESERVATION_CANCELLATION_HOURS)
        )

    def get_reservations_with_cancellation_info(
        self, reservations: list[Reservation]
    ) -> list[dict]:
        """Return reservations with cancellation eligibility information."""
        reservation_items = []
        for reservation in reservations:
            can_cancel = self.can_cancel_reservation(reservation).unwrap_or(False)
            reservation_items.append({
                'reservation': reservation,
                'can_cancel': can_cancel,
            })
        return reservation_items

    def fetch_reservation_detail(
        self, client_id: int, reservation_id: int
    ) -> Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]]:
        """Fetch a reservation detail by its ID."""
        result = self._fetch_reservation_detail(
            client_id=client_id, reservation_id=reservation_id
        )
        if result.is_err():
            return Result.Ok(
                RedirectResultDTO(
                    url='reservations_history',
                    messages=[MessageDTO(typ='error', msg=result.unwrap_err().msg)],
                )
            )
        res = result.unwrap()
        return Result.Ok(
            TemplateRenderResultDTO(
                template_name='cancel_reservation.html',
                context={
                    'reservation': res,
                    'can_cancel': self.can_cancel_reservation(res).unwrap_or(False),
                },
            )
        )

    def fetch_client_active_reservations(
        self, client_id: int, include_scheduled: bool
    ) -> Result[list[Reservation]]:
        """Fetch all active reservations for a client."""
        return self._fetch_client_active_reservations(client_id, include_scheduled)

    def fetch_client_reservation_history(self, client_id: int) -> Result[list[Reservation]]:
        """Fetch all reservations for a client."""
        return self._fetch_client_reservation_history(client_id)

    def cancel_reservation(
        self, reservation_id: int, client_id: int, reason: str = ''
    ) -> Result[TemplateRenderResultDTO | RedirectResultDTO]:
        res = self._cancel_reservation(reservation_id, client_id, reason)
        if res.is_err():
            return Result.Ok(
                RedirectResultDTO(
                    url='reservations_history',
                    messages=[MessageDTO(typ='error', msg=res.unwrap_err().msg)],
                )
            )
        self.logger.info(f'reservation {res.unwrap().id} cancelled')
        return Result.Ok(
            RedirectResultDTO(
                url='reservations_history',
                messages=[
                    MessageDTO(typ='success', msg=str(ReservationMessages.CANCELED_SUCCESS))
                ],
            )
        )
