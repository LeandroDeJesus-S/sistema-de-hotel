from abc import abstractmethod
from typing import Protocol

from exc import Result


class AbsRateLimiter(Protocol):
    """
    Interface for rate limiting mechanisms.
    """

    @abstractmethod
    def check_cooldown(self, key: str, ttl_seconds: int) -> Result[None]:
        """
        Checks if a specific action (identified by key) is in cooldown.
        If not, it sets the cooldown for the specified duration.

        Args:
            key: Unique identifier for the action/user (e.g., 'email_reset_user@example.com')
            ttl_seconds: Time-to-live for the cooldown in seconds.

        Returns:
            Result.Ok(None) if allowed (and cooldown set).
            Result.Err("Cooldown active") if the action is blocked.
        """
        ...
