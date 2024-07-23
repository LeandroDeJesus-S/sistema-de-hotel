import logging
# from typing import Any
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseServerError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from reservas.models import Reserva, Quarto
import stripe
from stripe.checkout import Session
from utils.supportviews import PaymentMessages
from utils.supportmodels import SessionKeys
from django.contrib import messages
# from clientes.models import Cliente
# from django.core.serializers import deserialize
# from datetime import datetime
# from utils.support import clear_session_keys
from .models import Pagamento
from django.db import transaction


class Payment(View):
    def setup(self, request: HttpRequest, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('reservasLogger')
        self.template = 'checkout.html'
    
    def get(self, request:HttpRequest, reservation_pk: int, *args, **kwargs):
        reservation = get_object_or_404(Reserva, pk__exact=reservation_pk)
        self.logger.debug('renderizando checkout.html')
        return render(request, self.template, {'reservation': reservation})

    @transaction.atomic
    def post(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        stripe.api_key = settings.STRIPE_API_KEY_SECRET
        
        reservation = get_object_or_404(Reserva, pk=reservation_pk)
        reservation.status = 'P'
        reservation.save()

        payment = Pagamento(reserva=reservation, valor=reservation.custo, status='p')
        payment.save()

        request.session[SessionKeys.RESERVATION_ID] = reservation.pk
        request.session.save()

        baseurl = f'http://{self.request.get_host()}'
        success_url = baseurl + reverse('payment_success', args=(reservation.pk,))
        cancel_url = baseurl + reverse('payment_cancel', args=(reservation.pk,))

        self.logger.debug(f'success callback url: {success_url}')
        self.logger.debug(f'cancel callback url: {cancel_url}')

        prod_name = f'Reserva: Quarto Nº{reservation.quarto.numero}, classe {reservation.quarto.classe}.'
        params = {
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'line_items': [
                    {
                        'adjustable_quantity': {
                            'enabled': False,
                        },
                        'price_data': {
                            'currency': 'brl',
                            'product_data': {
                                'name': prod_name,
                            }, 
                            'unit_amount': reservation.quarto.daily_price_in_cents, 
                        },
                        'quantity': reservation.reservation_days
                    }
                ]
            }
        
        try:
            stripe_session = Session.create(**params)
        except Exception as e:
            messages.error(request, PaymentMessages.PAYMENT_FAIL)
            return HttpResponse(str(e))
        
        return redirect(stripe_session.url)


def payment_success(request: HttpRequest, reservation_pk: int):
    logger = logging.getLogger('reservasLogger')
    logger.info(f'reserva {reservation_pk} recebida para sucesso de pagamento')

    payment = Pagamento.objects.get(reserva__pk=reservation_pk)
    payment.reserva.status = 'F'
    payment.reserva.ativa = True
    payment.reserva.save()
    
    payment.status = 'f'
    payment.save()

    logger.debug(f'renderizando pagina de sucesso com pagamento: {payment}')
    return render(request, 'success.html', {'payment': payment})


def payment_cancel(request: HttpRequest, reservation_pk: int):
    logger = logging.getLogger('reservasLogger')
    logger.info(f'reserva {reservation_pk} recebida para cancelamento')

    payment = Pagamento.objects.get(reserva__pk=reservation_pk)
    payment.reserva.status = 'C'
    payment.reserva.ativa = False
    payment.reserva.quarto.disponivel = False
    payment.reserva.save()

    payment.status = 'c'
    payment.save()

    logger.info(f'pagamento {payment} para a reserva {payment.reserva} cancelado')
    return render(request, 'cancel.html')
