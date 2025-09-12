import logging

from clients.feedback_messages import SignIn as SignInMessages
from exc import Error, Result

from ..domain import entities, ports
from .dtos import ChangePasswordInput, SignInInput


class AuthenticateUserUseCase:
    """Handles user authentication and session creation."""

    def __init__(
        self,
        repo: ports.AbsClientRepository,
        session_mng: ports.AbsSessionManager,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            repo: The repository for accessing client data.
            session_mng: The port for managing user sessions.
        """
        self._repo = repo
        self._session_mng = session_mng

    def __call__(self, data: dict) -> Result[entities.Client | None]:
        """
        Executes the sign-in process.

        Args:
            data: A dictionary containing the user's credentials.

        Returns:
            A Result containing the authenticated Client entity, or an Error on failure.
        """
        validated_data = SignInInput.safe_validate(data)
        if validated_data.error:
            return Result(
                value=None, error=Error(validated_data.error.msg, validated_data.error)
            )

        if validated_data.value is None:
            return Result(
                value=None,
                error=Error('Validation failed', None),
            )

        client, err = self._session_mng.authenticate(
            validated_data.value.username, validated_data.value.password
        )
        if err is not None or not client:
            return Result(
                value=None, error=Error(SignInMessages.INVALID_CREDENTIALS, src_error=err)
            )

        return entities.Client.safe_validate(client.__dict__)


class CreateUserUseCase:
    """Handles new user registration."""

    def __init__(
        self,
        repo: ports.AbsClientRepository,
        pw_mng: ports.AbsPasswordManager,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            repo: The repository for persisting the new client.
            pw_mng: The port for hashing passwords.
        """
        self._repo = repo
        self._pw_mng = pw_mng

    def __call__(self, user: entities.Client) -> Result[entities.Client | None]:
        """
        Executes the sign-up process.

        Args:
            user: The Client entity with the new user's information.
                  The `password` attribute should be the raw, unhashed password.
        Returns:
            A Result containing the created and persisted Client entity, or an Error on failure
        """
        ok, _ = self._repo.check_duplicate(user)
        if ok:
            return Result(
                value=None,
                error=Error(
                    'Não foi possível criar a conta. Verifique seus dados e tente novamente.'
                ),
            )

        hashed_password, err = self._pw_mng.hash_password(user.password)
        if err is not None or not hashed_password:
            return Result(value=None, error=Error('Failed to hash password', err))

        user.password = hashed_password
        u, err = self._repo.add(user)

        if err is not None:
            logging.getLogger('djangoLogger').error(err, exc_info=True)
            return Result(value=None, error=Error(err.msg, err))

        if u is None:
            return Result(value=None, error=Error('Failed to create user', err))

        return Result(value=u, error=None)


class ChangePasswordUseCase:
    """Handles changing a user's password."""

    def __init__(
        self,
        repo: ports.AbsClientRepository,
        pw_mng: ports.AbsPasswordManager,
        session_mng: ports.AbsSessionManager,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            repo: The repository for accessing and updating client data.
            pw_mng: The port for password hashing and verification.
            session_mng: The port for re-logging the user in after the change.
        """
        self._repo = repo
        self._pw_mng = pw_mng
        self._session_mng = session_mng

    def __call__(self, inp: ChangePasswordInput) -> Result[entities.Client | None]:
        """
        Executes the password change process.

        Args:
            request: The framework-specific request object containing the session to be managed
            client_id: The ID of the client whose password is being changed.
            new_password: The new raw password to be set.

        Returns:
            A Result containing the updated Client entity, or an Error on failure.
        """
        client_id = inp.user_id
        new_password = inp.password

        u, err = self._repo.get_by_id(client_id)
        if u is None:
            return Result(value=None, error=Error('Client not found', err))

        hashed_password, err = self._pw_mng.hash_password(new_password)
        if err is not None:
            return Result(value=None, error=Error('Failed to hash password', err))

        _, err = self._repo.update(client_id, password=hashed_password)
        if err is not None:
            return Result(value=None, error=Error('Failed to update password', err))

        return Result(value=u, error=None)


class VerifyCaptchaUseCase:
    """Handles the verification of a captcha token."""

    def __init__(
        self,
        captcha_service: ports.AbsCaptchaVerifier,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            captcha_service: The port for the external captcha verification service.
        """
        self._captcha_service = captcha_service

    def __call__(self, captcha_token: str) -> Result[bool]:
        """
        Executes the captcha verification process.

        Args:
            captcha_token: The token received from the captcha widget.

        Returns:
            A Result with True if the token is valid, or an Error on failure.
        """
        ok, err = self._captcha_service.verify(captcha_token)
        if not ok:
            return Result(value=False, error=Error('Captcha verification fail', err))

        return Result(value=True, error=None)
