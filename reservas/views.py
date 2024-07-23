from typing import Any
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import (
    redirect,
    render,
)
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from .models import (
    Beneficio,
    Classe,
    Quarto,
    Reserva
)
from .validators import convert_date


class Quartos(ListView):
    logger = logging.getLogger('reservasLogger')

    model = Quarto
    template_name = 'quartos.html'
    context_object_name = 'rooms_available'
    ordering = '-preco_diaria'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['benefits'] = Beneficio.objects.all()
        self.logger.debug('add benefits para o context')
        return context


class QuartoDetail(DetailView):
    model = Quarto
    template_name = 'quarto.html'
    context_object_name = 'quarto'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['benefits'] = Beneficio.objects.all()
        return context


class Reservar(LoginRequiredMixin, View):
    login_url = reverse_lazy('signin')
    permission_denied_message = 'Você não tem permissão para prosseguir.'

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('reservasLogger')
        self.context = {
            'room_classes': Classe.objects.all(),
        }
        self.template_name = 'reserva.html'

    def get(self, request: HttpRequest, quarto_pk: int):
        self.context['quarto_pk'] = quarto_pk
        return render(request, self.template_name, self.context)
    
    @transaction.atomic
    def post(self, request: HttpRequest, quarto_pk: int):
        self.context['quarto_pk'] = quarto_pk

        CHECK_IN = convert_date(self.request.POST.get('checkin', '0001-01-01'))
        CHECKOUT = convert_date(self.request.POST.get('checkout', '0001-01-01'))

        OBS = self.request.POST.get('obs', '')

        reservation = Reserva(
            check_in=CHECK_IN, 
            checkout=CHECKOUT,
            observacoes=OBS,
            cliente=self.request.user,
            quarto=Quarto.objects.get(pk__exact=quarto_pk),
        )
        try:
            reservation.full_clean()
        except ValidationError as e:
            messages.error(request, e.messages[0])
            self.logger.error(e.messages[0])
            return render(request, self.template_name, self.context)
        
        reservation.custo = reservation.calc_reservation_value()
        reservation.save()

        self.logger.info('reserva registrada. Redirecionando para checkout')
        return redirect(reverse_lazy('checkout', args=(reservation.pk,)))
