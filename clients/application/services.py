import logging

from clients.application.dtos import ChangePasswordInput, SignInInput, SignUpInput
from clients.application.usecases import (
    # AuthenticateUserUseCase,
    ChangePasswordUseCase,
    CreateUserUseCase,
    VerifyCaptchaUseCase,
)
from clients.domain.entities import Client as DomainClient
from clients.domain.ports import (
    AbsCaptchaVerifier,
    AbsClientRepository,
    AbsPasswordManager,
    AbsSessionManager,
)
from clients.feedback_messages import SignUp
from exc import Result


class ClientService:
    def __init__(
        self,
        repo: AbsClientRepository,
        password_manager: AbsPasswordManager,
        session_manager: AbsSessionManager,
        captcha_service: AbsCaptchaVerifier,
        logger: logging.Logger,
    ):
        self.create_user = CreateUserUseCase(repo, password_manager, logger)
        self.change_pw = ChangePasswordUseCase(repo, password_manager, session_manager)
        self.captcha = VerifyCaptchaUseCase(captcha_service)
        self.session_manager = session_manager
        self._repo = repo
        self.logger = logger

    def signup_user(self, form_data: dict, request) -> Result[str]:
        """
        Handle complete user signup process: validation, creation, and login.

        Args:
            form_data: Raw form data from the request
            request: Django HttpRequest object

        Returns:
            Result with redirect URL on success, or error message on failure
        """
        # Extract and validate input data
        input_data = {
            'username': form_data.get('username', '').strip(),
            'password': form_data.get('password', ''),
            'first_name': form_data.get('nome', '').strip(),
            'last_name': form_data.get('sobrenome', '').strip(),
            'phone': form_data.get('telefone', '').strip(),
            'email': form_data.get('email', '').strip(),
            'birthdate': form_data.get('nascimento', ''),
            'cpf': form_data.get('cpf', '').strip(),
        }

        # Validate required fields
        if not all(input_data.values()):
            return Result.Err(msg=SignUp.MISSING_FIELDS)

        # Validate input data with DTO
        signup_input_result = SignUpInput.safe_validate(input_data)
        if signup_input_result.is_err():
            return Result.Err(msg=signup_input_result.unwrap_err().msg)

        validated_input = signup_input_result.unwrap()

        # Create domain entity
        client_entity_result = DomainClient.safe_create(
            username=validated_input.username,
            password=validated_input.password,
            first_name=validated_input.first_name,
            last_name=validated_input.last_name,
            phone=validated_input.phone,
            birthdate=validated_input.birthdate,
            email=validated_input.email,
            cpf=validated_input.cpf,
        )
        if client_entity_result.is_err():
            return Result.Err(msg=client_entity_result.unwrap_err().msg)

        # Create user
        created_user_result = self.create_user(client_entity_result.unwrap())
        if created_user_result.is_err():
            return Result.Err(msg=created_user_result.unwrap_err().msg)

        # Log user in
        login_result = self.session_manager.login(request, created_user_result.unwrap())
        if login_result.is_err():
            return Result.Err(msg=login_result.unwrap_err().msg)

        return Result.Ok('rooms')

    def signin_user(self, credentials: dict, request) -> Result[str]:
        """
        Handle complete signin process: authentication, login, and redirect.

        Args:
            credentials: Dict with 'username' and 'password'
            request: Django HttpRequest object

        Returns:
            Result with redirect URL on success, or error message on failure
        """
        # Validate input data with DTO
        signin_input_result = SignInInput.safe_validate(credentials)
        if signin_input_result.is_err():
            return Result.Err(msg=signin_input_result.unwrap_err().msg)

        validated_credentials = signin_input_result.unwrap()

        # Authenticate user
        user_result = self.session_manager.authenticate(
            request,
            username=validated_credentials.username,
            password=validated_credentials.password,
        )
        if user_result.is_err():
            return Result.Err(msg=user_result.unwrap_err().msg)

        # Log user in
        login_result = self.session_manager.login(request, user_result.unwrap())
        if login_result.is_err():
            return Result.Err(msg=login_result.unwrap_err().msg)

        # Get next URL
        next_url = request.session.get('next_url', 'rooms')
        return Result.Ok(next_url)

    def process_password_change(self, form_data: dict, user_id: int) -> Result[None]:
        """
        Process password change request with validation.

        Args:
            form_data: Raw form data from the request
            user_id: ID of the user changing password

        Returns:
            Result with None on success, or error message on failure
        """
        data = {
            'user_id': user_id,
            'password': form_data.get('new_password', '').strip(),
            'password_repeat': form_data.get('password_repeat', '').strip(),
        }

        inp_result = ChangePasswordInput.safe_validate(data)
        if inp_result.is_err():
            return Result.Err(msg=inp_result.unwrap_err().msg)

        change_pw_result = self.change_pw(inp_result.unwrap())
        if change_pw_result.is_err():
            return Result.Err(msg=change_pw_result.unwrap_err().msg)

        return Result.Ok(None)
