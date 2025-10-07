from clients.domain.ports import AbsClientRepository
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
