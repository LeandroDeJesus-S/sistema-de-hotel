import logging
from http import HTTPStatus
from typing import Any

import requests
from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password, make_password

from clients.domain.entities import Client
from exc import Error, Result

logger = logging.getLogger('djangoLogger')


class DjangoPasswordManager:
    """Handles password hashing and verification using Django's built-in tools."""

    def hash_password(self, raw_password: str) -> Result[str | None]:  # noqa: PLR6301
        """
        Hashes a password using Django's PBKDF2 algorithm.

        Args:
            password: The raw password to hash.

        Returns:
            A Result containing the hashed password, or an Error on failure.
        """
        try:
            hashed = make_password(raw_password)
            return Result(value=hashed, error=None)
        except Exception as e:
            return Result(value=None, error=Error('Failed to hash password', e))

    def check_password(self, password: str, hashed: str) -> Result[bool]:  # noqa: PLR6301
        """
        Verifies a password against a hashed password.

        Args:
            password: The raw password to verify.
            hashed: The hashed password to check against.

        Returns:
            A tuple containing a boolean indicating success and an error, if any.
        """
        try:
            is_valid = check_password(password, hashed)
            if not is_valid:
                return Result(value=False, error=Error('Password does not match'))
            return Result(value=True, error=None)
        except Exception as e:
            return Result(value=False, error=Error('Failed to verify password', e))


class GoogleRecaptchaV3Verifier:
    """Verifies captcha tokens using Google's reCAPTCHA v3 service."""

    __URL = 'https://www.google.com/recaptcha/api/siteverify'
    __REQUEST_TIMEOUT_SECONDS = 5

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def verify(self, captcha_token: str) -> Result[bool]:
        """
        Verifies a captcha token using Google's reCAPTCHA v3 service.

        Args:
            captcha_token: The token received from the captcha widget.

        Returns:
            A Result with True if the token is valid, or an Error on failure.
        """
        response = requests.post(
            self.__URL,
            data={'secret': self.secret_key, 'response': captcha_token},
            timeout=self.__REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != HTTPStatus.OK:
            return Result(value=False, error=Error('Failed to verify captcha'))

        result = response.json()
        if not result.get('success'):
            return Result(value=False, error=Error('Invalid captcha'))

        return Result(value=True, error=None)


class DjangoSessionManager:
    """Manages user sessions using Django's built-in authentication system."""

    DEFAULT_BACKEND = 'clients.authenticator.UserEmailAuthBackend'

    def __init__(self, backend: str = DEFAULT_BACKEND) -> None:
        self._backend = backend
        self._usermodel = get_user_model()

    def authenticate(
        self, request: Any, username: str, password: str
    ) -> Result[Client | None]:
        logger.debug(f'authenticating user with backend: {self._backend}')
        try:
            user = django_authenticate(
                request,
                username=username,
                password=password,
                backend=self._backend,
            )
            if user is None:
                logger.debug(f'used credentials: {username} {password}')
                return Result(value=None, error=Error('Invalid credentials'))

            u = Client.model_validate(user.__dict__)
            return Result(value=u, error=None)
        except Exception as e:
            return Result(value=None, error=Error('Failed to validate user', e))

    def login(self, request: Any, user: Client) -> Result[None]:
        """
        Logs a user in by creating a session.

        Args:
            request: The framework-specific request object containing the session to be managed
            user: The user entity to log in.

        Returns:
            A Result indicating success or an Error on failure.
        """
        db_u = self._usermodel.objects.filter(id=user.id).first()
        if db_u is None:
            return Result(value=None, error=Error('Invalid user'))

        try:
            django_login(request, db_u, backend=self._backend)
            return Result(value=None, error=None)
        except Exception as e:
            return Result(value=None, error=Error('Failed to login user', e))

    def logout(self, request: Any) -> Result[None]:  # noqa: PLR6301
        """
        Logs a user out by clearing their session.

        Args:
            request: The framework-specific request object containing the session to be cleared

        Returns:
            A Result indicating success or an Error on failure.
        """
        try:
            django_logout(request)
            return Result(value=None, error=None)
        except Exception as e:
            return Result(value=None, error=Error('Failed to logout user', e))
