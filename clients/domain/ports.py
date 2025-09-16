"""
This module defines the ports (interfaces) and entities for the client domain.

Ports are the boundaries of the application's core logic (the hexagon).
They define the contracts that the driving adapters (e.g., web views) and
driven adapters (e.g., database repositories, external services) must adhere to.

Entities are the core business objects of the domain.
"""

from abc import abstractmethod
from typing import Any, Protocol

from exc import Result

from .entities import Client


class AbsClientRepository(Protocol):
    """
    A port that defines the contract for data persistence operations for Client entities.
    This is a driven port, implemented by an adapter in the infrastructure layer.
    """

    @abstractmethod
    def add(self, client: Client) -> Result[Client | None]:
        """
        Adds a new client to the repository and returns the persisted entity,
        which may include a database-assigned ID.
        """
        ...

    @abstractmethod
    def get_by_id(self, client_id: int) -> Result[Client | None]:
        """Retrieves a client by their unique ID."""
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> Result[Client | None]:
        """Retrieves a client by their username."""
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> Result[Client | None]:
        """Retrieves a client by their email address."""
        ...

    @abstractmethod
    def update(self, client_id: int, **kwargs: Any) -> Result[None]:
        """Updates an existing client's data in the repository."""
        ...

    @abstractmethod
    def delete(self, client_id: int) -> Result[None]:
        """Deletes a client from the repository by their ID."""
        ...

    @abstractmethod
    def check_duplicate(self, client: Client) -> Result[bool]:
        """Checks if a client with the same email or username already exists."""
        ...


class AbsPasswordManager(Protocol):
    """
    A port for password management operations, abstracting the hashing and
    verification logic. This is a driven port.
    """

    @abstractmethod
    def hash_password(self, raw_password: str) -> Result[str | None]:
        """Hashes a raw password and returns the secure hash."""
        ...

    @abstractmethod
    def check_password(self, raw_password: str, hashed_password: str) -> Result[bool]:
        """Checks if a raw password matches a hashed password."""
        ...


class AbsCaptchaVerifier(Protocol):
    """
    A port for verifying responses from an external captcha service.
    This is a driven port.
    """

    @abstractmethod
    def verify(self, captcha_token: str) -> Result[bool]:
        """
        Verifies the provided captcha token with the external service.
        Returns True if the token is valid, otherwise False.
        """
        ...


class AbsSessionManager(Protocol):
    """
    A port for managing user sessions, such as logging in and out.
    This is a driven port, implemented by an adapter that interacts with the
    web framework's session handling.
    """

    @abstractmethod
    def authenticate(
        self, request: Any, username: str, password: str
    ) -> Result[Client | None]:
        """
        Authenticates a user by their username and password.
        Returns the Client entity if authentication is successful, otherwise None.
        """
        ...

    @abstractmethod
    def login(self, request: Any, client: Client) -> Result[None]:
        """
        Logs the user in and attaches them to the current session.
        The adapter is responsible for handling the framework-specific request object
        and mapping the domain Client to the framework's user model if needed.
        """
        ...

    @abstractmethod
    def logout(self, request: Any) -> Result[None]:
        """Logs the user out and clears their session."""
        ...
