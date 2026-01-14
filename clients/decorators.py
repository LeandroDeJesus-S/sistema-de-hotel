import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from dependency_injector.wiring import Provide, inject
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from clients.container import ClientsContainer


@inject
def _check_perfil_ownership(
    request: HttpRequest,
    received_pk: int,
    logger: logging.Logger = Provide[ClientsContainer.logger],
) -> None:
    """Function that checks if the received profile is the same
    profile that sent the request."""
    if request.user.is_authenticated and request.user.pk != received_pk:
        logger.warning('user has no permission to access this profile')
        raise PermissionDenied


def profile_ownership_required(profile_pk_arg: str = 'pk'):
    """Decorator to check profile ownership."""

    def decorator(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view_func)
        def _wrapped_view(
            request: HttpRequest,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            _check_perfil_ownership(request, kwargs.get(profile_pk_arg, 0))
            return view_func(request, *args, **kwargs)

        return _wrapped_view  # type: ignore

    return decorator
