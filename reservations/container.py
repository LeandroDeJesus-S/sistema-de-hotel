import logging

from dependency_injector import containers, providers

# Infrastructure imports
from clients.infra.repo import ClientRepository

# Application imports
from payments.infra.repo import PaymentRepository
from reservations.application.services import ReservationService
from reservations.application.usecases import (
    ActivateReservationUseCase,
    CancelReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.infra.repo import ReservationRepository, RoomRepository
from utils.adapters.email import DjangoEmailSender
from utils.adapters.queue import DjangoQTaskQueuer
from utils.adapters.unit_of_work import UnitOfWork


class ReservationsContainer(containers.DeclarativeContainer):
    """Reservations module dependency injection container."""

    config = providers.Configuration()
    logger = providers.Object(logging.getLogger('djangoLogger'))

    # Infrastructure services
    client_repo = providers.Singleton(ClientRepository)
    reservation_repo = providers.Singleton(ReservationRepository)
    room_repo = providers.Singleton(RoomRepository)
    payment_repo = providers.Singleton(PaymentRepository)
    unit_of_work = providers.Singleton(UnitOfWork)
    task_queuer = providers.Singleton(DjangoQTaskQueuer)
    email_sender = providers.Singleton(DjangoEmailSender)

    release_reservation_usecase = providers.Singleton(
        ReleaseReservationUseCase,
        room_repo=room_repo,
        reservations_repo=reservation_repo,
        payments_repo=payment_repo,
        unit_of_work=unit_of_work,
    )
    schedule_reservation_usecase = providers.Singleton(
        ScheduleReservationUseCase,
        reservation_repo=reservation_repo,
        unit_of_work=unit_of_work,
        task_queuer=task_queuer,
    )
    activate_reservation_usecase = providers.Singleton(
        ActivateReservationUseCase,
        reservation_repo=reservation_repo,
        room_repo=room_repo,
        unit_of_work=unit_of_work,
    )

    # Application services
    reservation_service = providers.Factory(
        ReservationService,
        reservation_repo=reservation_repo,
        room_repo=room_repo,
        client_repo=client_repo,
        uow=unit_of_work,
    )
    cancel_reservation_usecase = providers.Singleton(
        CancelReservationUseCase,
        reservation_repo=reservation_repo,
        room_repo=room_repo,
        payments_repo=payment_repo,
        unit_of_work=unit_of_work,
        task_queuer=task_queuer,
    )
