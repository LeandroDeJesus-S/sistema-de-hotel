from typing import Any
from datetime import timedelta
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import (
    redirect,
    render,
)
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django_q.tasks import schedule

from .models import (
    Beneficio,
    Classe,
    Quarto,
    Reserva
)
from .validators import convert_date
from utils.supportviews import ReservaMessages, ReservaSupport


class Quartos(ListView):
    logger = logging.getLogger('djangoLogger')

    model = Quarto
    template_name = 'quartos.html'
    context_object_name = 'rooms_available'
    ordering = '-preco_diaria'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['benefits'] = Beneficio.objects.all()
        self.logger.debug('add benefits para o context')
        return context

    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        return qs.filter(disponivel=True)


class QuartoDetail(DetailView):
    model = Quarto
    template_name = 'quarto.html'
    context_object_name = 'quarto'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['benefits'] = Beneficio.objects.all()
        return context


class LoginRequired(LoginRequiredMixin):
    login_url = reverse_lazy('signin')


class Reservar(LoginRequired, View):
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.context = {
            'room_classes': Classe.objects.all(),
        }
        self.template_name = 'reserva.html'

    def get(self, request: HttpRequest, quarto_pk: int):
        self.context['quarto_pk'] = quarto_pk
        return render(request, self.template_name, self.context)

    def post(self, request: HttpRequest, quarto_pk: int):
        self.context['quarto_pk'] = quarto_pk

        CHECK_IN = convert_date(self.request.POST.get('checkin', '0001-01-01'))
        CHECKOUT = convert_date(self.request.POST.get('checkout', '0001-01-01'))
        OBS = self.request.POST.get('obs', '')
        
        try:
            with transaction.atomic():
                reservation = Reserva(
                    check_in=CHECK_IN, 
                    checkout=CHECKOUT,
                    observacoes=OBS,
                    cliente=self.request.user,
                    quarto=Quarto.objects.get(pk__exact=quarto_pk),
                )
                
                reservation.custo = reservation.calc_reservation_value()
                reservation.full_clean()
                reservation.save()

            schedule(
                'reservas.tasks.release_room', 
                reservation.pk,
                repeats=1,
                next_run=timezone.now() + timedelta(minutes=ReservaSupport.RESERVATION_PATIENCE_MINUTES)
            )

            self.logger.info('reserva registrada. Redirecionando para checkout')
            return redirect(reverse_lazy('checkout', args=(reservation.pk,)))

        except ValidationError as e:
            messages.error(request, e.messages[0])
            self.logger.error(e.messages[0])
            return render(request, self.template_name, self.context)
        
        except Exception as e:
            messages.error(request, ReservaMessages.RESERVATION_FAIL)
            room_url = reverse_lazy('quarto', args=(quarto_pk,))
            redirect_url = request.META.get('HTTP_REFERER', room_url)
            return redirect(redirect_url)


class HistoricoReservas(LoginRequired, ListView):
    model = Reserva
    template_name = 'historico_reservas.html'
    context_object_name = 'reservas'
    ordering = '-id'

    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        return qs.filter(cliente__exact=self.request.user)


class HistoricoReserva(LoginRequired, DetailView):
    model = Reserva
    context_object_name = 'reserva'
    template_name = 'historico_reserva.html'
