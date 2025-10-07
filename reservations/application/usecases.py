from decimal import Decimal

from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from exc import Error, Result
from utils.support import ensure_result

from ..domain.entities import Reservation
from ..domain.repo import AbsReservationRepository, AbsRoomRepository
from .dtos import CreateReservationInput


class InitializeReservationUseCase:
    def __init__(
        self,
        reservation_repo: AbsReservationRepository,
        room_repo: AbsRoomRepository,
        client_repo: AbsClientRepository,
        unit_of_work: AbsUnitOfWork,
    ):
        self.reservation_repo = reservation_repo
        self.room_repo = room_repo
        self.client_repo = client_repo
        self.unit_of_work = unit_of_work

    @ensure_result('Unexpected error while creating reservation')
    def __call__(self, command: CreateReservationInput) -> Result[Reservation | None]:  # noqa: PLR0911
        """Fetches the room, check if its available then checks for overlapping reservations
        and creates the reservation"""
        client, err = self.client_repo.get_by_id(command.client_id)
        if err is not None or not client:
            return Result(value=None, error=Error(msg='client not found', src_error=err))

        room_result = self.room_repo.find_by_id(command.room_pk)
        if room_result.error or not room_result.value:
            return Result(
                value=None, error=Error(msg='room not found', src_error=room_result.error)
            )

        if not room_result.value.available:
            return Result(value=None, error=Error(msg='room not available', src_error=None))

        room = room_result.value
        overlap_result = self.reservation_repo.has_overlapping_reservation(
            room_id=command.room_pk,
            check_in=command.check_in,
            check_out=command.check_out,
        )
        if overlap_result.error or overlap_result.value:
            return Result(
                value=None,
                error=Error(msg='The room is not available', src_error=None),
            )

        stayed_days = Decimal(str((command.check_out - command.check_in).days))
        reservation_entity, err = Reservation.safe_create(
            client=client,
            room=room,
            checkin=command.check_in,
            checkout=command.check_out,
            observations=command.observations,
            amount=room.daily_price * stayed_days,
        )

        if err or reservation_entity is None:
            return Result(value=None, error=err)

        with self.unit_of_work:
            saved_reservation_result = self.reservation_repo.save(reservation_entity)
            if saved_reservation_result.error or not saved_reservation_result.value:
                raise Error(
                    msg='failed to save reservation',
                    src_error=saved_reservation_result.error,
                )

            saved_reservation = saved_reservation_result.value

            room.available = False
            room_save_result = self.room_repo.save(room)
            if room_save_result.error:
                raise Error(
                    msg='failed to update room availability',
                    src_error=room_save_result.error,
                )

        return Result(value=saved_reservation, error=None)


class FetchClientActiveReservations:
    def __init__(self, repository: AbsReservationRepository):
        self._repo = repository

    def __call__(self, client_id: int, include_scheduled: bool) -> Result[list]:
        return self._repo.fetch_active_reservations(client_id, include_scheduled)


class ReleaseRoomUseCase:  # TODO: to implement it
    def __init__(self, repo: AbsRoomRepository) -> None:
        self._repo = repo

    def __call__(self) -> None:
        pass


class FetchClientReservationHistoryUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, client_id: int) -> Result[list[Reservation]]:
        return self._repo.fetch_client_history(client_id)


class FetchReservationDetailUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, reservation_id: int, client_id: int) -> Result[Reservation | None]:
        return self._repo.fetch_for_history_detail(client_id, reservation_id)
