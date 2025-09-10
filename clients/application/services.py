from clients.application.usecases import (
    AuthenticateUserUseCase,
    ChangePasswordUseCase,
    CreateUserUseCase,
    VerifyCaptchaUseCase,
)
from clients.domain.ports import (
    AbsCaptchaVerifier,
    AbsClientRepository,
    AbsPasswordManager,
    AbsSessionManager,
)


class ClientService:
    def __init__(
        self,
        repo: AbsClientRepository,
        password_manager: AbsPasswordManager,
        session_manager: AbsSessionManager,
        captcha_service: AbsCaptchaVerifier,
    ):
        self.authenticate_user = AuthenticateUserUseCase(repo, session_manager)
        self.create_user = CreateUserUseCase(repo, password_manager)
        self.change_pw = ChangePasswordUseCase(repo, password_manager, session_manager)
        self.captcha = VerifyCaptchaUseCase(captcha_service)
        self.session_manager = session_manager
