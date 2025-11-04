import logging
from decimal import Decimal
from typing import Dict

from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.domain.ports import AbsPaymentsRepository
from reservations import feedback_messages
from reservations.domain.entities import Reservation
from reservations.domain.value_objects import ReservationStatusEnum

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

    def __call__(self, command: CreateReservationInput) -> Result[Reservation]:
        """Fetches the room, check if its available then checks for overlapping reservations
        and creates the reservation"""
        return (
            self._find_client(command)
            .then(self._find_room)
            .then(self._check_availability)
            .then(self._check_overlap)
            .then(self._create_reservation_entity)
            .then(self._save_reservation)
        )

    def _find_client(self, command: CreateReservationInput) -> Result[Dict]:
        client_result = self.client_repo.get_by_id(command.client_id)
        if client_result.is_err():
            return Result.Err(msg='client not found', src_error=client_result.unwrap_err())
        return Result.Ok({'command': command, 'client': client_result.unwrap()})

    def _find_room(self, data: Dict) -> Result[Dict]:
        command = data['command']
        room_result = self.room_repo.find_by_id(command.room_pk)
        if room_result.is_err() or not room_result.unwrap():
            return Result.Err(msg='room not found', src_error=room_result.unwrap_err())
        data['room'] = room_result.unwrap()
        return Result.Ok(data)

    def _check_availability(self, data: Dict) -> Result[Dict]:  # noqa: PLR6301
        if not data['room'].available:
            return Result.Err(msg='room not available')
        return Result.Ok(data)

    def _check_overlap(self, data: Dict) -> Result[Dict]:
        command = data['command']
        overlap_result = self.reservation_repo.has_overlapping_reservation(
            room_id=command.room_pk,
            check_in=command.check_in,
            check_out=command.check_out,
        )
        if overlap_result.is_err() or overlap_result.unwrap():
            return Result.Err(msg='The room is not available')
        return Result.Ok(data)

    def _create_reservation_entity(self, data: Dict) -> Result[Reservation]:  # noqa: PLR6301
        command = data['command']
        client = data['client']
        room = data['room']

        result = Reservation.safe_create(
            client=client,
            room=room,
            checkin=command.check_in,
            checkout=command.check_out,
            observations=command.observations,
            amount=Decimal(
                '0'
            ),  # bypass to be sure that checkin/checkout are valid validates at first
            status=ReservationStatusEnum.INITIALIZED,
        )
        if result.is_err():
            return Result.Err(
                msg=feedback_messages.ReservationMessages.RESERVATION_FAIL,
                src_error=result.unwrap_err(),
            )

        reservation = result.unwrap()
        stayed_days = Decimal(str((command.check_out - command.check_in).days))
        reservation.amount = room.daily_price * stayed_days
        return Result.Ok(reservation)

    def _save_reservation(self, reservation_entity: Reservation) -> Result[Reservation]:
        logging.getLogger('djangoLogger').info('Saving reservation')
        with self.unit_of_work as uow:
            saved_reservation_result = self.reservation_repo.save(reservation_entity)
            if saved_reservation_result.is_err() or not saved_reservation_result.unwrap():
                uow.rollback()
                return Result.Err(
                    msg='failed to save reservation',
                    src_error=saved_reservation_result.unwrap_err(),
                )

            return Result.Ok(saved_reservation_result.unwrap())


class FetchClientActiveReservations:
    def __init__(self, repository: AbsReservationRepository):
        self._repo = repository

    def __call__(self, client_id: int, include_scheduled: bool) -> Result[list]:
        return self._repo.fetch_active_reservations(client_id, include_scheduled)


class ReleaseRoomUseCase:
    def __init__(
        self,
        room_repo: AbsRoomRepository,
        reservations_repo: AbsReservationRepository,
        payments_repo: AbsPaymentsRepository,
        unit_of_work: AbsUnitOfWork,
    ) -> None:
        self._room_repo = room_repo
        self._reservation_repo = reservations_repo
        self._payment_repo = payments_repo
        self._unit_of_work = unit_of_work
        self._logger = logging.getLogger('djangoLogger')

    def __call__(self, room_id: int) -> Result[bool]:
        with self._unit_of_work as uow:
            room_result = self._room_repo.find_by_id(room_id)
            if room_result.is_err():
                return Result.Err('Room not found', src_error=room_result.unwrap_err())

            room = room_result.unwrap()
            if room.available:
                return Result.Ok(True)

            room.available = True
            room_save_result = self._room_repo.save(room)

            if room_save_result.is_err():
                uow.rollback()
                return Result.Err(
                    msg='Failed to save room state',
                    src_error=room_save_result.unwrap_err(),
                )
            return Result.Ok(True)


class FetchClientReservationHistoryUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, client_id: int) -> Result[list[Reservation]]:
        return self._repo.fetch_client_history(client_id)


class FetchReservationDetailUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, reservation_id: int, client_id: int) -> Result[Reservation]:
        return self._repo.fetch_for_history_detail(client_id, reservation_id)
