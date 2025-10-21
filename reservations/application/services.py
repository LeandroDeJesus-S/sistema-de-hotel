from typing import Any, Dict

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

        result = self.initialize_reservation(command.unwrap())
        if result.is_err():
            return Result.Err(result.unwrap_err().msg, result.unwrap_err())

        return Result.Ok(result.unwrap())
