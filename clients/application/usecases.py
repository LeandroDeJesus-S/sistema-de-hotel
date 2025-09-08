import logging
from typing import Any

from clients.domain import entities
from exc import Error, Result

from ..domain import ports


class SignInUserUseCase:
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

    def __call__(
        self, request: Any, username: str, password: str
    ) -> Result[entities.Client | None]:
        """
        Executes the sign-in process.

        Args:
            request: The framework-specific request object containing the session to be managed
            username: The user's username.
            password: The user's raw password.

        Returns:
            A Result containing the authenticated Client entity, or an Error on failure.
        """
        client, err = self._session_mng.authenticate(username, password)
        if err is not None or not client:
            return Result(value=None, error=Error('Authentication failed', src_error=err))

        self._session_mng.login(request, client)
        return entities.Client.safe_validate(client)


class SignUpUserUseCase:
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
        ok, err = self._repo.check_duplicate(user)
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


class LogoutUserUseCase:
    """Handles user logout by clearing their session."""

    def __init__(
        self,
        session_mng: ports.AbsSessionManager,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            session_mng: The port for managing user sessions.
        """
        self._session_mng = session_mng

    def __call__(self, request: Any) -> Result[None]:
        """
        Executes the logout process.

        Args:
            request: The framework-specific request object containing the session to be cleared
        """
        return self._session_mng.logout(request)


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

    def __call__(
        self, request: Any, client_id: int, new_password: str
    ) -> Result[entities.Client | None]:
        """
        Executes the password change process.

        Args:
            request: The framework-specific request object containing the session to be managed
            client_id: The ID of the client whose password is being changed.
            new_password: The new raw password to be set.

        Returns:
            A Result containing the updated Client entity, or an Error on failure.
        """
        u, err = self._repo.get_by_id(client_id)
        if u is None:
            return Result(value=None, error=Error('Client not found', err))

        hashed_password, err = self._pw_mng.hash_password(new_password)
        if err is not None:
            return Result(value=None, error=Error('Failed to hash password', err))

        _, err = self._repo.update(client_id, password=hashed_password)
        if err is not None:
            return Result(value=None, error=Error('Failed to update password', err))
        _, err = self._session_mng.login(request, u)

        if err is not None:
            return Result(value=None, error=Error('Failed to login user', err))

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
