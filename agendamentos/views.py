from typing import Any
from django.http import HttpRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from reservas.models import Reserva, Quarto
from reservas.validators import convert_date


class Agendar(View):
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.context = {}
    
    def get(self, _, quarto_pk, *args, **kwargs):
        self.context['quarto_pk'] = quarto_pk
        return render(self.request, 'agendamentos.html', self.context)

    def post(self, _, quarto_pk, *args, **kwargs):
        self.context['quarto_pk'] = quarto_pk

        CHECK_IN = convert_date(self.request.POST.get('checkin', '0001-01-01'))
        CHECKOUT = convert_date(self.request.POST.get('checkout', '0001-01-01'))
        OBS = self.request.POST.get('obs', '')

        reservation = Reserva(
            check_in=CHECK_IN, 
            checkout=CHECKOUT,
            observacoes=OBS,
            cliente=self.request.user,
            quarto=get_object_or_404(Quarto, pk__exact=quarto_pk),
        )

        # TODO: validar reserva e agendamento
        return redirect('/')

