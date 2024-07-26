from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from reservas.models import Reserva


def check_reservation_ownership(view):
    @wraps(view)
    def _wrapped_view(request, *args, **kwargs):
        reservation = get_object_or_404(Reserva, pk=kwargs.get('reservation_pk'))
        if reservation.cliente != request.user:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return _wrapped_view
