import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def _check_perfil_ownership(request: HttpRequest, received_pk: int) -> None:
    """função que verifica se o perfil recebido é o mesmo
    perfil que enviou o request."""
    if request.user.is_authenticated and request.user.pk != received_pk:
        logging.getLogger('djangoLogger').warning(f'{request.user.pk} != {received_pk}')
        raise PermissionDenied


def profile_ownership_required(profile_pk_arg: str = 'pk'):
    """Decorator para verificar a propriedade do perfil."""

    def decorator(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            _check_perfil_ownership(request, kwargs.get(profile_pk_arg, 0))
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
