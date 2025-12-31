import logging

from clients.feedback_messages import ClientErrorMessages
from exc import Error, Result

from ..domain import entities, ports
from .dtos import ChangePasswordInput


class CreateUserUseCase:
    """Handles new user registration."""

    def __init__(
        self,
        repo: ports.AbsClientRepository,
        pw_mng: ports.AbsPasswordManager,
        logger: logging.Logger,
    ) -> None:
        """
        Initializes the use case with its dependencies.

        Args:
            repo: The repository for persisting the new client.
            pw_mng: The port for hashing passwords.
            logger: The logger instance.
        """
        self._repo = repo
        self._pw_mng = pw_mng
        self._logger = logger

    def __call__(self, user: entities.Client) -> Result[entities.Client]:
        """
        Executes the sign-up process.

        Args:
            user: The Client entity with the new user's information.
                  The `password` attribute should be the raw, unhashed password.
        Returns:
            A Result containing the created and persisted Client entity, or an Error on failure
        """
        duplicate_result = self._repo.check_duplicate(user)
        if duplicate_result.is_err():
            return Result.Err(
                msg=duplicate_result.unwrap_err().msg,
                src_error=duplicate_result.unwrap_err().src_error,
            )
        if duplicate_result.unwrap():  # A duplicate was found
            return Result.Err(
                msg=ClientErrorMessages.SIGNUP_ERROR,
                src_error=Error(msg='Duplicate user data'),
            )

        hashed_password_result = self._pw_mng.hash_password(user.password)
        if hashed_password_result.is_err():
            return Result.Err(
                msg='Failed to hash password', src_error=hashed_password_result.unwrap_err()
            )

        user.password = hashed_password_result.unwrap()
        add_result = self._repo.add(user)

        if add_result.is_err():
            self._logger.error(add_result.unwrap_err(), exc_info=True)
            return Result.Err(
                msg=add_result.unwrap_err().msg,
                src_error=add_result.unwrap_err(),
            )

        return add_result


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

    def __call__(self, inp: ChangePasswordInput) -> Result[entities.Client]:
        """
        Executes the password change process.

        Args:
            inp: The input data for the password change.

        Returns:
            A Result containing the updated Client entity, or an Error on failure.
        """
        client_result = self._repo.get_by_id(inp.user_id)
        if client_result.is_err():
            return Result.Err(msg='Client not found', src_error=client_result.unwrap_err())

        hashed_password_result = self._pw_mng.hash_password(inp.password)
        if hashed_password_result.is_err():
            return Result.Err(
                msg='Failed to hash password', src_error=hashed_password_result.unwrap_err()
            )

        update_result = self._repo.update(
            inp.user_id, password=hashed_password_result.unwrap()
        )
        if update_result.is_err():
            return Result.Err(
                msg='Failed to update password', src_error=update_result.unwrap_err()
            )

        return client_result


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
        return self._captcha_service.verify(captcha_token)
