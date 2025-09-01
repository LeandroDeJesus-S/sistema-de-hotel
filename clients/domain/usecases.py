from typing import Any, Protocol

from clients.domain import entities

from . import ports


class SignInUserUseCase(Protocol):
    """Handles user authentication and session creation."""

    def __init__(
        self,
        repo: ports.AbsClientRepository,
        pw_mng: ports.AbsPasswordManager,
        session_mng: ports.AbsSessionManager,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            repo: The repository for accessing client data.
            pw_mng: The port for password hashing and verification.
            session_mng: The port for managing user sessions.
        """
        ...

    def __call__(self, username: str, password: str) -> ports.Client | None:
        """
        Executes the sign-in process.

        Args:
            username: The user's username.
            password: The user's raw password.

        Returns:
            The authenticated Client entity if successful, otherwise None.
        """
        ...


class SignUpUserUseCase(Protocol):
    """Handles new user registration and session creation."""

    def __init__(
        self,
        repo: ports.AbsClientRepository,
        pw_mng: ports.AbsPasswordManager,
        session_mng: ports.AbsSessionManager,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            repo: The repository for persisting the new client.
            pw_mng: The port for hashing passwords.
            session_mng: The port for managing user sessions.
        """
        ...

    def __call__(self, user: entities.Client) -> ports.Client | None:
        """
        Executes the sign-up process.

        Args:
            user: The Client entity with the new user's information.
                  The `password` attribute should be the raw, unhashed password.

        Returns:
            The created and persisted Client entity, or None on failure.
        """
        ...


class LogoutUserUseCase(Protocol):
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
        ...

    def __call__(self, request: Any) -> None:
        """
        Executes the logout process.

        Args:
            request: The framework-specific request object containing the session to be cleared
        """
        ...


class ChangePasswordUseCase(Protocol):
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
        ...

    def __call__(self, client_id: int, old_password: str, new_password: str) -> bool:
        """
        Executes the password change process.

        Args:
            client_id: The ID of the client whose password is being changed.
            old_password: The user's current raw password for verification.
            new_password: The new raw password to be set.

        Returns:
            True if the password was changed successfully, False otherwise.
        """
        ...


class VerifyCaptchaUseCase(Protocol):
    """Handles the verification of a captcha token."""

    def __init__(
        self,
        captcha_service: ports.AbsCaptchaService,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            captcha_service: The port for the external captcha verification service.
        """
        ...

    def __call__(self, captcha_token: str) -> bool:
        """
        Executes the captcha verification process.

        Args:
            captcha_token: The token received from the captcha widget.

        Returns:
            True if the token is valid, False otherwise.
        """
        ...
