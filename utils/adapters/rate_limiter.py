from django.core.cache import cache

from base.ports.rate_limiter import AbsRateLimiter
from exc import Result


class DjangoCacheRateLimiter(AbsRateLimiter):
    """
    Rate limiter implementation using Django's cache framework.
    """

    def check_cooldown(self, key: str, ttl_seconds: int) -> Result[None]:
        """
        Tries to add the key to the cache.
        cache.add returns True if the key was added (didn't exist),
        and False if it already existed.
        """
        # We use 'add' because it only sets the value if it doesn't exist.
        # This is perfect for a cooldown lock.
        is_allowed = cache.add(key, 'active', timeout=ttl_seconds)

        if is_allowed:
            return Result.Ok(None)

        return Result.Err('Too many requests. Please try again later.')
