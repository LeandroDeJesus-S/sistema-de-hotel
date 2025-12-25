import logging

from dependency_injector import containers, providers
from django.conf import settings

# Service imports
from clients.application.services import ClientService
from clients.infra.adapters import (
    DjangoPasswordManager,
    DjangoSessionManager,
    GoogleRecaptchaV3Verifier,
)

# Infrastructure imports
from clients.infra.repo import ClientRepository
from payments.application.services import PaymentService
from payments.application.usecases import SendPaymentConfirmationUseCase
from payments.infra.adapters import StripeCheckoutSession, StripePaymentWebhookHandler
from payments.infra.repo import PaymentRepository
from reservations.application.services import ReservationService
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


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""

    # Infrastructure Layer (Singletons - shared across app)
    client_repo = providers.Singleton(ClientRepository)
    reservation_repo = providers.Singleton(ReservationRepository)
    room_repo = providers.Singleton(RoomRepository)
    payment_repo = providers.Singleton(PaymentRepository)
    unit_of_work = providers.Singleton(UnitOfWork)
    password_manager = providers.Singleton(DjangoPasswordManager)
    session_manager = providers.Singleton(DjangoSessionManager)
    captcha_service = providers.Singleton(
        GoogleRecaptchaV3Verifier, secret_key=settings.G_RECAPTCHA_KEY_SECRET
    )
    payment_gateway = providers.Singleton(
        StripeCheckoutSession, stripe_api_key=settings.STRIPE_API_KEY_SECRET
    )
    webhook_handler = providers.Singleton(StripePaymentWebhookHandler)
    task_queuer = providers.Singleton(DjangoQTaskQueuer)
    email_sender = providers.Singleton(DjangoEmailSender)
    pdf_generator = providers.Singleton(ReportLabPDFReceiptGenerator)
    logger = providers.Object(logging.getLogger('djangoLogger'))

    # Application Layer (Factories - new instance per injection)
    client_service = providers.Factory(
        ClientService,
        repo=client_repo,
        password_manager=password_manager,
        session_manager=session_manager,
        captcha_service=captcha_service,
    )
    reservation_service = providers.Factory(
        ReservationService,
        reservation_repo=reservation_repo,
        room_repo=room_repo,
        client_repo=client_repo,
        uow=unit_of_work,
    )
    # Payment use cases (singletons since they don't hold state)
    confirmation_usecase = providers.Singleton(
        SendPaymentConfirmationUseCase,
        email_sender=email_sender,
        pdf_generator=pdf_generator,
    )
    activate_reservation_usecase = providers.Singleton(
        ActivateReservationUseCase,
        reservation_repo=reservation_repo,
        room_repo=room_repo,
        uow=unit_of_work,
    )
    schedule_reservation_usecase = providers.Singleton(
        ScheduleReservationUseCase,
        reservation_repo=reservation_repo,
        uow=unit_of_work,
        task_queuer=task_queuer,
    )
    release_reservation_usecase = providers.Singleton(
        ReleaseReservationUseCase,
        room_repo=room_repo,
        reservation_repo=reservation_repo,
        payment_repo=payment_repo,
        uow=unit_of_work,
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
