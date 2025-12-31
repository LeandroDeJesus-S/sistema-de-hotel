import logging

from dependency_injector import containers, providers

# Infrastructure imports
from clients.infra.repo import ClientRepository
from payments.application.services import PaymentService
from payments.application.usecases import SendPaymentConfirmationUseCase
from payments.infra.adapters import StripeCheckoutSession, StripePaymentWebhookHandler
from payments.infra.repo import PaymentRepository
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.infra.repo import ReservationRepository, RoomRepository
from utils.adapters.email import DjangoEmailSender
from utils.adapters.pdf import ReportLabPDFReceiptGenerator
from utils.adapters.queue import DjangoQTaskQueuer
from utils.adapters.unit_of_work import UnitOfWork


class PaymentsContainer(containers.DeclarativeContainer):
    """Application dependency injection container."""

    config = providers.Configuration()

    # Infrastructure Layer (Singletons - shared across app)
    logger = providers.Object(logging.getLogger('djangoLogger'))
    client_repo = providers.Singleton(ClientRepository, logger=logger)
    reservation_repo = providers.Singleton(ReservationRepository)
    room_repo = providers.Singleton(RoomRepository)
    payment_repo = providers.Singleton(PaymentRepository)
    unit_of_work = providers.Singleton(UnitOfWork)
    payment_gateway = providers.Singleton(
        StripeCheckoutSession,
        stripe_api_key=config.STRIPE_API_KEY_SECRET,
        logger=logger,
    )
    webhook_handler = providers.Singleton(StripePaymentWebhookHandler, logger=logger)
    task_queuer = providers.Singleton(DjangoQTaskQueuer)
    email_sender = providers.Singleton(DjangoEmailSender)
    pdf_generator = providers.Singleton(ReportLabPDFReceiptGenerator)

    confirmation_usecase = providers.Factory(
        SendPaymentConfirmationUseCase,
        mailer=email_sender,
        pdf_generator=pdf_generator,
    )
    activate_reservation_usecase = providers.Singleton(
        ActivateReservationUseCase,
        reservation_repo=reservation_repo,
        room_repo=room_repo,
        unit_of_work=unit_of_work,
    )
    schedule_reservation_usecase = providers.Singleton(
        ScheduleReservationUseCase,
        reservation_repo=reservation_repo,
        unit_of_work=unit_of_work,
        task_queuer=task_queuer,
    )
    release_reservation_usecase = providers.Singleton(
        ReleaseReservationUseCase,
        room_repo=room_repo,
        reservation_repo=reservation_repo,
        payment_repo=payment_repo,
        unit_of_work=unit_of_work,
    )
    payment_service = providers.Factory(
        PaymentService,
        payment_gateway=payment_gateway,
        payment_repo=payment_repo,
        uow=unit_of_work,
        logger=logger,
        reservation_repo=reservation_repo,
        client_repo=client_repo,
        wh_handler=webhook_handler,
    )
