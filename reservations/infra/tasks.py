from typing import Optional

from base.ports.queue import TaskQueuer
from base.ports.unit_of_work import AbsUnitOfWork
from exc import Result
from payments.domain.ports import AbsPaymentsRepository
from payments.infra.repo import PaymentRepository
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.domain.repo import AbsReservationRepository, AbsRoomRepository
from reservations.infra.repo import ReservationRepository, RoomRepository
from utils.adapters.queue import DjangoQTaskQueuer
from utils.adapters.unit_of_work import UnitOfWork


def get_reservation_repository() -> AbsReservationRepository:
    return ReservationRepository()


def get_room_repository() -> AbsRoomRepository:
    return RoomRepository()


def get_payment_repository() -> AbsPaymentsRepository:
    return PaymentRepository()


def get_unit_of_work() -> AbsUnitOfWork:
    return UnitOfWork()


def get_task_queuer() -> TaskQueuer:
    return DjangoQTaskQueuer()


def activate_reservation_task(
    reservation_id: int,
    reservation_repo: Optional[AbsReservationRepository] = None,
    room_repo: Optional[AbsRoomRepository] = None,
    unit_of_work: Optional[AbsUnitOfWork] = None,
) -> Result[None]:
    """
    Activates a reservation by setting its status to ACTIVE and making the room unavailable.

    Args:
        reservation_id: The ID of the reservation to activate.
        reservation_repo: Optional. The reservation repository to use. Defaults to
            ReservationRepository.
        room_repo: Optional. The room repository to use. Defaults to RoomRepository.
        unit_of_work: Optional. The unit of work to use. Defaults to UNIT_OF_WORK.

    Returns:
        A Result indicating success or failure.
    """
    reservation_repo = reservation_repo or get_reservation_repository()
    room_repo = room_repo or get_room_repository()
    unit_of_work = unit_of_work or get_unit_of_work()

    usecase = ActivateReservationUseCase(
        reservation_repo=reservation_repo,
        room_repo=room_repo,
        unit_of_work=unit_of_work,
    )

    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err()

    reservation = reservation_result.unwrap()
    res = usecase(reservation)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)


def release_reservation_task(
    reservation_id: int,
    room_repo: Optional[AbsRoomRepository] = None,
    reservation_repo: Optional[AbsReservationRepository] = None,
    payment_repo: Optional[AbsPaymentsRepository] = None,
    unit_of_work: Optional[AbsUnitOfWork] = None,
) -> Result[None]:
    """
    Releases a reservation by setting its status to finished and making the room available.

    Args:
        reservation_id: The ID of the reservation to release.
        room_repo: Optional. The room repository to use. Defaults to RoomRepository.
        reservation_repo: Optional. The reservation repository to use. Defaults to
            ReservationRepository.
        payment_repo: Optional. The payment repository to use. Defaults to PaymentRepository.
        unit_of_work: Optional. The unit of work to use. Defaults to UnitOfWork.

    Returns:
        A Result indicating success or failure.
    """
    room_repo = room_repo or get_room_repository()
    reservation_repo = reservation_repo or get_reservation_repository()
    payment_repo = payment_repo or get_payment_repository()
    unit_of_work = unit_of_work or get_unit_of_work()

    usecase = ReleaseReservationUseCase(
        room_repo=room_repo,
        reservations_repo=reservation_repo,
        payments_repo=payment_repo,
        unit_of_work=unit_of_work,
    )

    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err()

    reservation = reservation_result.unwrap()
    res = usecase(reservation)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)


def schedule_reservation_task(reservation_id: int) -> Result[None]:
    """
    Schedules a reservation by setting its status to scheduled and making the reservation
    active.

    Args:
        reservation_id: The ID of the reservation to schedule.

    Returns:
        A Result indicating success or failure.
    """
    reservation_repo = get_reservation_repository()
    unit_of_work = get_unit_of_work()
    task_queuer = get_task_queuer()

    usecase = ScheduleReservationUseCase(
        reservation_repo=reservation_repo,
        unit_of_work=unit_of_work,
        task_queuer=task_queuer,
    )

    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err()

    reservation = reservation_result.unwrap()
    res = usecase(reservation)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)
