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

from clients.infra.repo import ClientRepository
from reservations.application.dtos import CreateReservationInput
from reservations.infra.repo import ReservationRepository, RoomRepository
from utils import support
from utils.adapters.unit_of_work import UnitOfWork

from .application import services
from .feedback_messages import ReservationMessages
from .mixins import LoginRequired
from .models import Room
from .validators import convert_date

svc = services.ReservationService(
    reservation_repo=ReservationRepository(),
    room_repo=RoomRepository(),
    client_repo=ClientRepository(),
    uow=UnitOfWork(),
)


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
        ).unwrap()

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
        if result.is_err():
            err = result.unwrap_err()
            self.logger.error(err.msg, exc_info=err.src_error)
            messages.error(self.request, 'Could not load rooms.')
            return []

        rooms = result.unwrap()
        self.logger.debug(f'{rooms =}')
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
            room_classes = []
        else:
            room_classes = result.unwrap()

        self.context: dict[str, Any] = {
            'room_classes': room_classes,
        }
        self.template_name = 'reserve.html'

    def get(self, request: HttpRequest, room_pk: int):
        """renderiza o formulário para nova reserva caso o usuário não
        tenha uma reserva ativa ou agendada"""
        result = svc.reservation_repo.has_active_reservation(
            client_id=request.user.pk, include_scheduled=True
        )
        if result.is_err():
            err = result.unwrap_err()
            self.logger.error(err, exc_info=err.src_error)
            messages.error(request, err.msg)
            return redirect('rooms')

        if result.unwrap():
            self.logger.info('user already have a reservation active ou scheduled')
            messages.info(request, ReservationMessages.ALREADY_HAVE_A_RESERVATION)
            return redirect('rooms')

        self.context['room_pk'] = room_pk
        self.context['recaptcha_site_key'] = settings.G_RECAPTCHA_KEY_SITE
        self.logger.debug(f'rendering {self.template_name}')
        return render(request, self.template_name, self.context)

    @method_decorator(support.captcha_required('reserve', params=('room_pk',)))
    def post(self, request: HttpRequest, room_pk: int):
        self.logger.debug(f'reservation for room {room_pk} started')
        self.context['room_pk'] = room_pk

        check_in_result = convert_date(request.POST.get('checkin', '0001-01-01'))
        checkout_result = convert_date(request.POST.get('checkout', '0001-01-01'))

        if check_in_result.is_err() or checkout_result.is_err():
            err = (
                check_in_result.unwrap_err()
                if check_in_result.is_err()
                else checkout_result.unwrap_err()
            )
            self.logger.error(f'failed to convert date {err.msg}')
            messages.error(request, err.msg)
            return redirect(reverse_lazy('reserve', args=(room_pk,)))

        obs = request.POST.get('obs', '')

        result = svc.initialize_reservation(
            CreateReservationInput(
                client_id=request.user.pk,
                room_pk=room_pk,
                check_in=check_in_result.unwrap(),
                check_out=checkout_result.unwrap(),
                observations=obs,
            )
        )
        if result.is_err():
            err = result.unwrap_err()
            msg = err.msg or 'unable to create reservation'
            self.logger.error(msg, exc_info=err.src_error)
            messages.error(request, msg)
            return render(request, self.template_name, self.context)

        reservation = result.unwrap()
        self.logger.info(f'reservation {reservation.id} registered. Redirecting to checkout')
        return redirect(reverse_lazy('checkout', args=(reservation.id,)))


class ReservationsHistory(LoginRequired, ListView):
    """exibe o histórico de reservas do usuário"""

    template_name = 'reservations_history.html'
    context_object_name = 'reservations'
    logger = logging.getLogger('djangoLogger')

    def get_queryset(self) -> list:
        result = svc.fetch_client_reservation_history(client_id=self.request.user.pk)
        if result.is_err():
            err = result.unwrap_err()
            self.logger.error(err.msg, exc_info=err.src_error)
            messages.error(self.request, 'Could not load reservation history.')
            return []

        reservations = result.unwrap()
        self.logger.debug(f'successfully loaded {len(reservations)} reservations')
        return reservations


class ReservationHistory(LoginRequired, DetailView):
    """exibe os dados de um reserva específica do histórico de reservas"""

    context_object_name = 'reservation'
    template_name = 'reservation_history.html'
    logger = logging.getLogger('djangoLogger')

    def get_object(self, _=None):
        result = svc.fetch_reservation_detail(
            reservation_id=self.kwargs.get('pk'), client_id=self.request.user.pk
        )
        if result.is_err():
            err = result.unwrap_err()
            self.logger.error(err.msg, exc_info=err.src_error)
            raise Http404(err.msg)

        reservation = result.unwrap()
        if not reservation:
            raise Http404('Reservation not found.')

        return reservation
