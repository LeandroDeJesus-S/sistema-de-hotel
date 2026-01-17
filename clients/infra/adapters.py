from http import HTTPStatus
from typing import Any, cast

import requests
from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator

from clients.domain.entities import Client
from exc import Result


class DjangoPasswordManager:
    """Handles password hashing and verification using Django's built-in tools."""

    def hash_password(self, raw_password: str) -> Result[str]:  # noqa: PLR6301
        """
        Hashes a password using Django's PBKDF2 algorithm.

        Args:
            password: The raw password to hash.

        Returns:
            A Result containing the hashed password, or an Error on failure.
        """
        try:
            hashed = make_password(raw_password)
            return Result.Ok(hashed)
        except Exception as e:
            return Result.Err('Failed to hash password', e)

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
                return Result.Err('Password does not match')
            return Result.Ok(True)
        except Exception as e:
            return Result.Err('Failed to verify password', e)


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
            return Result.Err('Failed to verify captcha')

        result = response.json()
        if not result.get('success'):
            return Result.Err('Invalid captcha')

        return Result.Ok(True)


class DjangoSessionManager:
    """Manages user sessions using Django's built-in authentication system."""

    DEFAULT_BACKEND = 'clients.authenticator.UserEmailAuthBackend'

    def __init__(self, backend: str = DEFAULT_BACKEND) -> None:
        self._backend = backend
        self._usermodel = get_user_model()

    def authenticate(self, request: Any, username: str, password: str) -> Result[Client]:
        try:
            user = django_authenticate(
                request,
                username=username,
                password=password,
                backend=self._backend,
            )
            if user is None:
                return Result.Err('Invalid credentials')

            u = Client.model_validate(user.__dict__)
            return Result.Ok(u)
        except Exception as e:
            return Result.Err('Failed to validate user', e)

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
            return Result.Err('Invalid user')

        try:
            django_login(request, db_u, backend=self._backend)
            return Result.Ok(None)
        except Exception as e:
            return Result.Err('Failed to login user', e)

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
            return Result.Ok(None)
        except Exception as e:
            return Result.Err('Failed to logout user', e)


class DjangoTokenManager:
    """Manages password reset tokens using Django's default generator."""

    def __init__(self):
        self._usermodel = get_user_model()

    def make_token(self, client: Client) -> str:
        """Generates a token for the given client."""
        user = self._usermodel.objects.get(id=client.id)
        return cast(str, default_token_generator.make_token(user))

    def check_token(self, client: Client, token: str) -> bool:
        """Checks if the token is valid for the given client."""
        try:
            user = self._usermodel.objects.get(id=client.id)
            return cast(bool, default_token_generator.check_token(user, token))
        except self._usermodel.DoesNotExist:
            return False
