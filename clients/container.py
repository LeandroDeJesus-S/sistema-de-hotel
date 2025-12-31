import logging

from dependency_injector import containers, providers

# Application imports
from clients.application.services import ClientService

# Infrastructure imports
from clients.infra.adapters import (
    DjangoPasswordManager,
    DjangoSessionManager,
    GoogleRecaptchaV3Verifier,
)
from clients.infra.repo import ClientRepository


class ClientsContainer(containers.DeclarativeContainer):
    """Clients module dependency injection container."""

    config = providers.Configuration()
    logger = providers.Object(logging.getLogger('djangoLogger'))

    # Infrastructure services
    client_repo = providers.Singleton(ClientRepository, logger=logger)
    password_manager = providers.Singleton(DjangoPasswordManager)
    session_manager = providers.Singleton(DjangoSessionManager)
    captcha_service = providers.Singleton(
        GoogleRecaptchaV3Verifier, secret_key=config.G_RECAPTCHA_KEY_SECRET
    )

    # Application services
    client_service = providers.Factory(
        ClientService,
        repo=client_repo,
        password_manager=password_manager,
        session_manager=session_manager,
        captcha_service=captcha_service,
        logger=logger,
    )
