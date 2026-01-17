import logging
from typing import Union

from base.dtos import MessageDTO, RedirectResultDTO, TemplateRenderResultDTO
from base.ports.queue import TaskQueuer
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
    AbsTokenManager,
)
from clients.feedback_messages import ChangePassword, SignUp
from exc import Result


class ClientService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        repo: AbsClientRepository,
        password_manager: AbsPasswordManager,
        session_manager: AbsSessionManager,
        captcha_service: AbsCaptchaVerifier,
        task_queuer: TaskQueuer,
        logger: logging.Logger,
        token_manager: AbsTokenManager,
    ):
        self.create_user = CreateUserUseCase(repo, password_manager, logger)
        self.change_pw = ChangePasswordUseCase(repo, password_manager, session_manager)
        self.captcha = VerifyCaptchaUseCase(captcha_service)
        self.session_manager = session_manager
        self.task_queuer = task_queuer
        self.token_manager = token_manager
        self._repo = repo
        self.logger = logger

    def request_magic_link(self, email: str, domain: str) -> Result[TemplateRenderResultDTO]:
        """
        Request a magic link for password change.

        Args:
            email: The email to send the link to.
            domain: The domain of the site.

        Returns:
            Result with TemplateRenderResultDTO
        """

        client_result = self._repo.get_by_email(email)

        if client_result.is_err():
            # generic message to avoid enumeration
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='request_magic_link.html',
                    context={},
                    messages=[
                        MessageDTO(
                            typ='success',
                            msg='If the email is registered, you will receive a link shortly.',
                        )
                    ],
                )
            )

        client = client_result.unwrap()
        token = self.token_manager.make_token(client)

        self.task_queuer.queue_task(
            'clients.infra.taskssend_password_change_email_task',
            (client.id, token, domain),
            name=f'send_password_change_email_{client.id}',
        )

        return Result.Ok(
            TemplateRenderResultDTO(
                template_name='request_magic_link.html',
                context={},
                messages=[
                    MessageDTO(
                        typ='success',
                        msg='If the email is registered, you will receive a link shortly.',
                    )
                ],
            )
        )

    def validate_magic_link_token(self, user_id: int, token: str) -> bool:
        """
        Validates the password change token.
        """
        client_result = self._repo.get_by_id(user_id)
        if client_result.is_err():
            self.logger.error(
                f'failed to validate magic link token: {client_result.unwrap_err().msg}'
            )
            return False

        client = client_result.unwrap()
        return self.token_manager.check_token(client, token)

    def signup_user(
        self, form_data: dict, request
    ) -> Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]]:
        """
        Handle complete user signup process: validation, creation, and login.

        Args:
            form_data: Raw form data from the request
            request: Django HttpRequest object

        Returns:
            Result with TemplateRenderResultDTO on error, RedirectResultDTO on success
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
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signup.html',
                    context={},
                    messages=[MessageDTO(typ='error', msg=str(SignUp.MISSING_FIELDS))],
                )
            )

        # Validate input data with DTO
        signup_input_result = SignUpInput.safe_validate(input_data)
        if signup_input_result.is_err():
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signup.html',
                    context={},
                    messages=[
                        MessageDTO(typ='error', msg=str(signup_input_result.unwrap_err().msg))
                    ],
                )
            )

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
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signup.html',
                    context={},
                    messages=[
                        MessageDTO(typ='error', msg=str(client_entity_result.unwrap_err().msg))
                    ],
                )
            )

        # Create user
        created_user_result = self.create_user(client_entity_result.unwrap())
        if created_user_result.is_err():
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signup.html',
                    context={},
                    messages=[
                        MessageDTO(typ='error', msg=str(created_user_result.unwrap_err().msg))
                    ],
                )
            )

        # Log user in
        login_result = self.session_manager.login(request, created_user_result.unwrap())
        if login_result.is_err():
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signup.html',
                    context={},
                    messages=[MessageDTO(typ='error', msg=str(login_result.unwrap_err().msg))],
                )
            )

        return Result.Ok(RedirectResultDTO(url='rooms'))

    def signin_user(
        self, credentials: dict, request
    ) -> Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]]:
        """
        Handle complete signin process: authentication, login, and redirect.

        Args:
            credentials: Dict with 'username' and 'password'
            request: Django HttpRequest object

        Returns:
            Result with TemplateRenderResultDTO on error, RedirectResultDTO on success
        """
        # Validate input data with DTO
        signin_input_result = SignInInput.safe_validate(credentials)
        if signin_input_result.is_err():
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signin.html',
                    context={},
                    messages=[
                        MessageDTO(typ='error', msg=str(signin_input_result.unwrap_err().msg))
                    ],
                )
            )

        validated_credentials = signin_input_result.unwrap()

        # Authenticate user
        user_result = self.session_manager.authenticate(
            request,
            username=validated_credentials.username,
            password=validated_credentials.password,
        )
        if user_result.is_err():
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signin.html',
                    context={},
                    messages=[MessageDTO(typ='error', msg=str(user_result.unwrap_err().msg))],
                )
            )

        # Log user in
        login_result = self.session_manager.login(request, user_result.unwrap())
        if login_result.is_err():
            return Result.Ok(
                TemplateRenderResultDTO(
                    template_name='signin.html',
                    context={},
                    messages=[MessageDTO(typ='error', msg=str(login_result.unwrap_err().msg))],
                )
            )

        # Get next URL
        next_url = request.session.get('next_url', 'rooms')
        return Result.Ok(RedirectResultDTO(url=next_url))

    def process_password_change(
        self, form_data: dict, user_id: int
    ) -> Result[RedirectResultDTO]:
        """
        Process password change request with validation.

        Args:
            form_data: Raw form data from the request
            user_id: ID of the user changing password

        Returns:
            Result with RedirectResultDTO on success or failure
        """
        data = {
            'user_id': user_id,
            'password': form_data.get('new_password', '').strip(),
            'password_repeat': form_data.get('password_repeat', '').strip(),
        }

        inp_result = ChangePasswordInput.safe_validate(data)
        if inp_result.is_err():
            return Result.Ok(
                RedirectResultDTO(
                    url='perfil',
                    messages=[MessageDTO(typ='error', msg=str(inp_result.unwrap_err().msg))],
                    args=(user_id,),
                )
            )

        change_pw_result = self.change_pw(inp_result.unwrap())
        if change_pw_result.is_err():
            return Result.Ok(
                RedirectResultDTO(
                    url='perfil',
                    messages=[
                        MessageDTO(typ='error', msg=str(change_pw_result.unwrap_err().msg))
                    ],
                    args=(user_id,),
                )
            )

        return Result.Ok(
            RedirectResultDTO(
                url='perfil',
                messages=[MessageDTO(typ='success', msg=str(ChangePassword.SUCCESS))],
                args=(user_id,),
            )
        )
