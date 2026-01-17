import logging

from dependency_injector import containers, providers

# Application imports
from clients.application.services import ClientService

# Infrastructure imports
from clients.infra.adapters import (
    DjangoPasswordManager,
    DjangoSessionManager,
    DjangoTokenManager,
    GoogleRecaptchaV3Verifier,
)
from clients.infra.repo import ClientRepository
from utils.adapters.email import DjangoEmailSender
from utils.adapters.queue import DjangoQTaskQueuer


class ClientsContainer(containers.DeclarativeContainer):
    """Clients module dependency injection container."""

    config = providers.Configuration()
    logger = providers.Object(logging.getLogger('djangoLogger'))

    # Infrastructure services
    client_repo = providers.Singleton(ClientRepository, logger=logger)
    password_manager = providers.Singleton(DjangoPasswordManager)
    session_manager = providers.Singleton(DjangoSessionManager)
    token_manager = providers.Singleton(DjangoTokenManager)
    captcha_service = providers.Singleton(
        GoogleRecaptchaV3Verifier, secret_key=config.G_RECAPTCHA_KEY_SECRET
    )
    task_queuer = providers.Singleton(DjangoQTaskQueuer)
    email_sender = providers.Singleton(DjangoEmailSender)

    # Application services
    client_service = providers.Factory(
        ClientService,
        repo=client_repo,
        password_manager=password_manager,
        session_manager=session_manager,
        captcha_service=captcha_service,
        task_queuer=task_queuer,
        logger=logger,
        token_manager=token_manager,
    )
