import logging
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from HOTEL import get_container
from payments.infra.repo import PaymentRepository
from reservations.domain.entities import Reservation
from reservations.infra.repo import ReservationRepository, RoomRepository
from utils import support
from utils.adapters.queue import DjangoQTaskQueuer
from utils.adapters.unit_of_work import UnitOfWork

from .application import services
from .application.usecases import CancelReservationUseCase
from .feedback_messages import ReservationMessages
from .mixins import LoginRequired
from .models import Room

svc = get_container().reservation_service()


def setup_reservation_context(
    request: HttpRequest, svc: services.ReservationService, context: dict[str, Any]
):
    """add the reservations to the context
    Args:
        request (HttpRequest)
        svc (ReservationService)
        context (Any): view context
    """
    if request.user.is_authenticated:
        context['reservation_on'] = svc.fetch_client_active_reservations(
            request.user.pk, include_scheduled=True
        ).unwrap_or([])

    context['benefits'] = svc.room_repo.fetch_all_benefits().unwrap_or([])


class Rooms(ListView):
    """lista todos os quartos da base de dados"""

    logger = logging.getLogger('djangoLogger')

    model = Room
    template_name = 'rooms.html'
    context_object_name = 'rooms'

    def get_queryset(self):
        """retorna todos os quartos com seus benefícios"""
        result = svc.room_repo.fetch_all(with_benefits=True)
        *_, rooms = result.match(
            on_ok=lambda rs: (
                self.logger.debug('successfully loaded rooms'),  # type: ignore
                rs,
            ),
            on_err=lambda err: (
                self.logger.error(err.msg, exc_info=err.src_error),  # type: ignore
                messages.error(self.request, 'Could not load rooms.'),
                [],
            ),
        )
        return rooms

    def get_context_data(self, **kwargs):
        """retorna todos os quartos, todos os benefícios e todas as reservas
        ativas ou agendadas do cliente, caso tenha.
        """
        context = super().get_context_data(**kwargs)
        setup_reservation_context(self.request, svc, context)
        return context


class RoomDetail(DetailView):
    """mostra os dados de um quarto em especifico"""

    model = Room
    template_name = 'room.html'
    context_object_name = 'room'

    def get_context_data(self, **kwargs):
        """add os benefícios e reservas ativas ou agendadas do cliente
        caso tenha
        """
        context = super().get_context_data(**kwargs)
        setup_reservation_context(self.request, svc, context)
        return context


@method_decorator(support.captcha_required('reserve', params=('room_pk',)), 'post')
class Reserve(LoginRequired, View):
    """gerencia a criação de novas reservas"""

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')

        result = svc.room_repo.fetch_all_classes()
        if result.is_err():
            err = result.unwrap_err()
            self.logger.error(err.msg, exc_info=err.src_error)
            messages.error(request, err.msg)

        self.context: dict[str, Any] = {'room_classes': result.unwrap_or([])}
        self.template_name = 'reserve.html'

    def get(self, request: HttpRequest, room_pk: int):
        """renderiza o formulário para nova reserva caso o usuário não
        tenha uma reserva ativa ou agendada"""
        result = svc.can_client_create_reservation(client_id=request.user.pk)

        def _on_ok(has):
            if has:
                self.logger.info('user already have a reservation active ou scheduled')
                messages.info(request, ReservationMessages.ALREADY_HAVE_A_RESERVATION)
                return redirect('rooms')

            self.context['room_pk'] = room_pk
            self.context['recaptcha_site_key'] = settings.G_RECAPTCHA_KEY_SITE
            self.logger.debug(f'rendering {self.template_name}')
            return render(request, self.template_name, self.context)

        def _on_err(err):
            self.logger.error(err.msg, exc_info=err.src_error)
            messages.error(request, err.msg)
            return redirect('rooms')

        response = result.match(
            on_ok=_on_ok,
            on_err=_on_err,
        )
        return response

    def post(self, request: HttpRequest, room_pk: int):
        self.logger.debug(f'reservation for room {room_pk} started')
        self.context['room_pk'] = room_pk

        result = svc.create_reservation({
            'client_id': request.user.pk,
            'room_pk': room_pk,
            'check_in': request.POST.get('checkin', '0001-01-01'),
            'check_out': request.POST.get('checkout', '0001-01-01'),
            'observations': request.POST.get('obs', ''),
        })
        *_, response = result.match(
            on_ok=lambda r: (
                self.logger.info(f'reservation {r.id} registered. Redirecting to checkout'),  # type: ignore
                redirect(reverse_lazy('checkout', args=(r.id,))),
            ),
            on_err=lambda err: (
                self.logger.error(err.msg, exc_info=err.src_error),  # type: ignore
                messages.error(request, err.msg),
                redirect(reverse_lazy('reserve', args=(room_pk,))),
            ),
        )
        return response


class ReservationsHistory(LoginRequired, ListView):
    """exibe o histórico de reservas do usuário"""

    template_name = 'reservations_history.html'
    context_object_name = 'reservations'
    logger = logging.getLogger('djangoLogger')

    def get_queryset(self) -> list[Reservation]:
        result = svc.fetch_client_reservation_history(client_id=self.request.user.pk)

        def _on_err(err) -> list[Reservation]:
            self.logger.error(err.msg, exc_info=err.src_error)
            messages.error(self.request, err.msg)
            return []

        reservations: list[Reservation] = result.match(
            on_ok=lambda rs: rs,
            on_err=_on_err,
        )
        return reservations

    def get_context_data(self, **kwargs):
        """Add cancellation eligibility information."""
        context = super().get_context_data(**kwargs)
        context['reservation_items'] = svc.get_reservations_with_cancellation_info(
            context['reservations']
        )
        return context


class ReservationHistory(LoginRequired, DetailView):
    """exibe os dados de um reserva específica do histórico de reservas"""

    context_object_name = 'reservation'
    template_name = 'reservation_history.html'
    logger = logging.getLogger('djangoLogger')

    def get_object(self, _=None):
        result = svc.fetch_reservation_detail(
            reservation_id=self.kwargs.get('pk'), client_id=self.request.user.pk
        )
        *_, reservation = result.match(
            on_ok=lambda r: (None, r),
            on_err=lambda err: (
                self.logger.error(err.msg, exc_info=err.src_error),  # Type: ignore
                Http404(err.msg),
            ),
        )
        return reservation


@method_decorator(support.captcha_required('cancel_reservation'), 'post')
class CancelReservationView(LoginRequired, View):
    """Handle reservation cancellation requests."""

    logger = logging.getLogger('djangoLogger')

    def get(self, request, pk):
        """Show cancellation confirmation page."""
        result = svc.fetch_reservation_detail(reservation_id=pk, client_id=request.user.pk)

        reservation = result.match(
            on_ok=lambda r: r,
            on_err=lambda err: (
                self.logger.error(err.msg, exc_info=err.src_error),
                messages.error(request, err.msg),
                None,
            ),
        )

        if not reservation:
            return redirect('reservations_history')

        # Check if reservation can be cancelled
        can_cancel = svc.can_cancel_reservation(reservation)

        context = {
            'reservation': reservation,
            'can_cancel': can_cancel,
        }

        return render(request, 'cancel_reservation.html', context)

    def post(self, request, pk):  # noqa: PLR6301
        """Process reservation cancellation."""
        reason = request.POST.get('reason', '').strip()

        # Initialize use case dependencies

        usecase = CancelReservationUseCase(
            reservation_repo=ReservationRepository(),
            room_repo=RoomRepository(),
            payments_repo=PaymentRepository(),
            unit_of_work=UnitOfWork(),
            task_queuer=DjangoQTaskQueuer(),
        )

        # Execute cancellation
        result = usecase(pk, request.user.pk, reason)

        if result.is_err():
            messages.error(request, result.unwrap_err().msg)
        else:
            messages.success(request, 'Reserva cancelada com sucesso.')

        return redirect('reservations_history')
