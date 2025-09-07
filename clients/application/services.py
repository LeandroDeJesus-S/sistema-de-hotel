from clients.application.usecases import (
    ChangePasswordUseCase,
    LogoutUserUseCase,
    SignInUserUseCase,
    SignUpUserUseCase,
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
        self.signin = SignInUserUseCase(repo, session_manager)
        self.signup = SignUpUserUseCase(repo, password_manager, session_manager)
        self.logout = LogoutUserUseCase(session_manager)
        self.change_pw = ChangePasswordUseCase(repo, password_manager, session_manager)
        self.captcha = VerifyCaptchaUseCase(captcha_service)
