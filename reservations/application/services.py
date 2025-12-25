from datetime import datetime, time, timedelta
from typing import Any, Dict

from django.conf import settings
from django.utils import timezone

from clients.domain.ports import AbsClientRepository
from exc import Result
from reservations.application.dtos import CreateReservationInput
from reservations.domain.entities import Reservation
from utils.adapters.unit_of_work import AbsUnitOfWork

from ..domain.repo import AbsReservationRepository, AbsRoomRepository
from .usecases import (
    FetchClientActiveReservations,
    FetchClientReservationHistoryUseCase,
    FetchReservationDetailUseCase,
    InitializeReservationUseCase,
)


class ReservationService:
    def __init__(
        self,
        reservation_repo: AbsReservationRepository,
        room_repo: AbsRoomRepository,
        client_repo: AbsClientRepository,
        uow: AbsUnitOfWork,
    ):
        self.reservation_repo = reservation_repo
        self.room_repo = room_repo
        self.client_repo = client_repo

        self.initialize_reservation = InitializeReservationUseCase(
            reservation_repo, room_repo, client_repo, uow
        )
        self.fetch_client_active_reservations = FetchClientActiveReservations(reservation_repo)
        self.fetch_client_reservation_history = FetchClientReservationHistoryUseCase(
            reservation_repo
        )
        self.fetch_reservation_detail = FetchReservationDetailUseCase(reservation_repo)

    def create_reservation(self, data: Dict[str, Any]) -> Result[Reservation]:
        command = CreateReservationInput.safe_validate(data)
        if command.is_err():
            return Result.Err(msg='invalid data', src_error=command.unwrap_err())

        cmd = command.unwrap()
        pending = self.reservation_repo.fetch_pending(
            cmd.client_id, cmd.room_pk, cmd.check_in, cmd.check_out
        ).unwrap_or(None)
        if pending:
            return Result.Ok(pending)

        result = self.initialize_reservation(command.unwrap())
        if result.is_err():
            return Result.Err(result.unwrap_err().msg, result.unwrap_err())

        return Result.Ok(result.unwrap())

    def can_client_create_reservation(self, client_id: int) -> Result[bool]:
        """Check if client can create a new reservation (no active/scheduled ones)."""
        return self.reservation_repo.has_active_reservation(
            client_id=client_id, include_scheduled=True
        )

    def can_cancel_reservation(self, reservation: Reservation) -> bool:
        """Determine if a specific reservation can be cancelled."""
        now = timezone.now()
        checkin_datetime = datetime.combine(reservation.checkin, time.min, tzinfo=now.tzinfo)
        time_diff = checkin_datetime - now
        return (
            reservation.status in {'A', 'S'}  # ACTIVE or SCHEDULED
            and time_diff >= timedelta(hours=settings.RESERVATION_CANCELLATION_HOURS)
        )

    def get_reservations_with_cancellation_info(
        self, reservations: list[Reservation]
    ) -> list[dict]:
        """Return reservations with cancellation eligibility information."""
        reservation_items = []
        for reservation in reservations:
            can_cancel = self.can_cancel_reservation(reservation)
            reservation_items.append({
                'reservation': reservation,
                'can_cancel': can_cancel,
            })
        return reservation_items
