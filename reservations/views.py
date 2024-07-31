from typing import Any
from datetime import timedelta
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.query import QuerySet, Q
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import (
    redirect,
    render,
    get_object_or_404
)
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django_q.tasks import schedule

from .mixins import LoginRequired
from .models import (
    Benefit,
    Class,
    Room,
    Reservation
)
from .validators import convert_date
from utils.supportviews import ReserveMessages, ReserveSupport


def get_user_reservations_on(request, context):
    """add ao context as reservas ativas ou agendadas de um usuário
    com a key `reservation_on`

    Args:
        request (HttpRequest)
        context (Any): view context
    """
    if request.user.is_authenticated:
        reservation_on = request.user.reservation_clients.filter(status__in=['A', 'S']).first()
        if reservation_on is not None:
            context['reservation_on'] = reservation_on


class Rooms(ListView):
    """lista todos os quartos da base de dados"""
    logger = logging.getLogger('djangoLogger')

    model = Room
    template_name = 'rooms.html'
    context_object_name = 'rooms'
    ordering = '-daily_price'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['benefits'] = Benefit.objects.all()
        self.logger.debug('add benefits to the context')

        get_user_reservations_on(self.request, context)
        return context


class RoomDetail(DetailView):
    """mostra os dados de um quarto em especifico"""
    model = Room
    template_name = 'room.html'
    context_object_name = 'room'

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')

    def get_context_data(self, **kwargs):
        """add os benefícios ao context para manuseio no html"""
        context = super().get_context_data(**kwargs)
        context['benefits'] = Benefit.objects.all()
        self.logger.info('add benefits to context')
        get_user_reservations_on(self.request, context)
        return context


class Reserve(LoginRequired, View):
    """gerencia a criação de novas reservas"""
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.context = {
            'room_classes': Class.objects.all(),
        }
        self.template_name = 'reserve.html'

    def get(self, request: HttpRequest, room_pk: int):
        """renderiza o formulário para nova reserva caso o usuário não
        tenha uma reserva ativa ou agendada"""
        if Reservation.objects.filter(client=request.user, status__in=['A', 'S']).exists():
            self.logger.info('user already have a reservation active ou scheduled')
            messages.info(request, ReserveMessages.ALREADY_HAVE_A_RESERVATION)
            return redirect('room')

        self.context['room_pk'] = room_pk
        self.logger.debug(f'rendering {self.template_name}')
        return render(request, self.template_name, self.context)

    def post(self, request: HttpRequest, room_pk: int):
        self.logger.debug(f'reservation for room {room_pk} started')
        self.context['room_pk'] = room_pk

        CHECK_IN = convert_date(self.request.POST.get('checkin', '0001-01-01'))
        CHECKOUT = convert_date(self.request.POST.get('checkout', '0001-01-01'))
        OBS = self.request.POST.get('obs', '')
        
        try:
            with transaction.atomic():
                reservation = Reservation(
                    checkin=CHECK_IN, 
                    checkout=CHECKOUT,
                    observations=OBS,
                    client=self.request.user,
                    room=get_object_or_404(Room, pk__exact=room_pk),
                )
                
                reservation.amount = reservation.calc_reservation_value()
                reservation.full_clean()
                reservation.save()
                self.logger.info(f'reservation {reservation} created')

            schd = schedule(
                'reservations.tasks.release_room', 
                reservation.pk,
                repeats=1,
                next_run=timezone.now() + timedelta(minutes=ReserveSupport.RESERVATION_PATIENCE_MINUTES)
            )
            self.logger.info(f'schedule {schd} created')
            self.logger.info(f'reservation {reservation.pk} registered. Redirecting to checkout')
            return redirect(reverse_lazy('checkout', args=(reservation.pk,)))

        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            self.logger.error(str(exc.error_dict))
            return render(request, self.template_name, self.context)
        
        except Exception as exc:
            self.logger.error(str(exc))
            messages.error(request, ReserveMessages.RESERVATION_FAIL)
            room_url = reverse_lazy('room', args=(room_pk,))
            redirect_url = request.META.get('HTTP_REFERER', room_url)
            return redirect(redirect_url)


class ReservationsHistory(LoginRequired, ListView):
    """exibe o histórico de reservas do usuário"""
    model = Reservation
    template_name = 'reservations_history.html'
    context_object_name = 'reservations'
    ordering = '-id'

    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        return qs.filter(client__exact=self.request.user)


class ReservationHistory(LoginRequired, DetailView):
    """exibe os dados de um reserva específica do histórico de reservas"""
    model = Reservation
    context_object_name = 'reservation'
    template_name = 'reservation_history.html'

    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        return qs.filter(client__exact=self.request.user)
