from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from exc import Result
from reservations.domain.entities import Reservation
from reservations.feedback_messages import ReservationMessages


def reserve_get_presenter(
    request: HttpRequest,
    result: Result[bool],
    template_name: str,
    context: dict[str, Any],
) -> Result[HttpResponse]:
    """Presenter for reserve get requests."""

    def _on_ok(can: bool) -> HttpResponse:
        if not can:
            messages.info(request, ReservationMessages.ALREADY_HAVE_A_RESERVATION)
            return redirect('rooms')
        return render(request, template_name, context)

    def _on_err(err) -> HttpResponse:
        messages.error(request, err.msg)
        return redirect('rooms')

    return Result.Ok(result.match(on_ok=_on_ok, on_err=_on_err))


def reserve_post_presenter(
    request: HttpRequest,
    result: Result[Reservation],
    fail_redirect_args: tuple,
) -> Result[HttpResponse]:
    """Presenter for reserve post requests."""

    def _on_ok(r: Reservation) -> HttpResponse:
        return redirect(reverse_lazy('checkout', args=(r.id,)))

    def _on_err(err) -> HttpResponse:
        messages.error(request, err.msg)
        return redirect(reverse_lazy('reserve', args=fail_redirect_args))

    return Result.Ok(result.match(on_ok=_on_ok, on_err=_on_err))


def cancel_reservation_get_presenter(
    request: HttpRequest,
    result: Result[Reservation],
    can_cancel: bool,
) -> Result[HttpResponse]:
    """Presenter for cancel reservation get requests."""

    def _on_ok(reservation: Reservation) -> HttpResponse:
        if not reservation:
            return redirect('reservations_history')

        context = {
            'reservation': reservation,
            'can_cancel': can_cancel,
        }
        return render(request, 'cancel_reservation.html', context)

    def _on_err(err) -> HttpResponse:
        messages.error(request, err.msg)
        return redirect('reservations_history')  # Fallback if error

    return Result.Ok(result.match(on_ok=_on_ok, on_err=_on_err))


def cancel_reservation_post_presenter(
    request: HttpRequest,
    result: Result[Any],
) -> Result[HttpResponse]:
    """Presenter for cancel reservation post requests."""

    if result.is_err():
        messages.error(request, result.unwrap_err().msg)
    else:
        messages.success(request, 'Reserva cancelada com sucesso.')

    return Result.Ok(redirect('reservations_history'))
