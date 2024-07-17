from typing import Any
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
import stripe.stripe_object
from reservas.models import Reserva, Quarto
from clientes.models import Cliente
from django.core.serializers import deserialize
from stripe.checkout import Session
import logging
from datetime import datetime


class Payment(View):
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.default_return = redirect(reverse('reserva'))
        self.logger = logging.getLogger('reservasLogger')
    
    def get(self, _, room_id, client_id, *args, **kwargs):
        # TODO: validar room_id, client_id

        reservation_json = self.request.session.get('reservation')
        self.logger.debug(
            f'quarto recebido: {room_id} :: reserva json recebida: \
            {reservation_json} :: client_id recebido: {client_id}'
        )
        
        if reservation_json is None:
            return self.default_return
        
        reservation = deserialize('json', reservation_json)
        reservation: Reserva = list(reservation)[0].object
            
        room = get_object_or_404(Quarto, pk__exact=room_id)  # ou da session
        client = get_object_or_404(Cliente, pk__exact=client_id)  # ou da session
        reservation.reserve(client, room)
        reservation.save()
        self.request.session['reservation_id'] = reservation.pk
        self.request.session.save()

        self.logger.debug(
            f'quarto {room} e cliente {client} atribuídos à: \
            reserva {reservation.pk} com custo: {reservation.custo}'
        )

        self.logger.debug('renderizando checkout.html')
        return render(self.request, 'checkout.html', {'reservation': reservation})

    def post(self, *args, **kwargs):
        stripe.api_key = settings.STRIPE_API_KEY_SECRET
        reservation_id = self.request.session.get('reservation_id')
        if not reservation_id:
            self.logger.warning('id da reserva não esta na sessão')
            return redirect('pre_reserva')
        
        reservation = get_object_or_404(Reserva, pk=reservation_id)  # processing
        self.logger.debug(f'reserva a ser paga: {reservation}')

        baseurl = f'http://{self.request.get_host()}'
        success_url = baseurl + reverse('payment_success')
        cancel_url = baseurl + reverse('payment_cancel')

        self.logger.debug(f'success callback url: {success_url}')
        self.logger.debug(f'cancel callback url: {cancel_url}')

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
                                'name': reservation.__str__(),
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
            return HttpResponse(str(e))
        
        return redirect(stripe_session.url)


def payment_success(request: HttpRequest):
    logger = logging.getLogger('reservasLogger')

    reservation_id = request.session['reservation_id']
    logger.debug(f'reservation id received: {reservation_id}')

    reservation = Reserva.objects.filter(pk__exact=reservation_id).first()
    logger.debug(f'reservation object: {reservation_id}')
    reservation.status = 'f'
    reservation.data_reserva = datetime.now()
    reservation.save()
    request.session.flush()
    request.session.save()
    return render(request, 'success.html')


def payment_cancel(request):
    return render(request, 'cancel.html')
