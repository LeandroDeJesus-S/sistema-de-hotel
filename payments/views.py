import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from reservas.models import Reserva
import stripe
from stripe.checkout import Session
from utils.supportviews import PaymentMessages
from django.contrib import messages
from .models import Pagamento
from django.db import transaction
from sqlite3 import OperationalError
from utils.supportviews import ReservaSupport


class Payment(View):
    def setup(self, request: HttpRequest, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template = 'checkout.html'
    
    def get(self, request:HttpRequest, reservation_pk: int, *args, **kwargs):
        reservation = get_object_or_404(Reserva, pk__exact=reservation_pk)
        self.logger.debug('renderizando checkout.html')
        return render(request, self.template, {'reservation': reservation})

    @transaction.atomic
    def post(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        try:
            stripe.api_key = settings.STRIPE_API_KEY_SECRET
            reservation = get_object_or_404(Reserva, pk=reservation_pk)
            reservation._validate_room()

            reservation.quarto.disponivel = False
            reservation.status = 'P'

            payment = Pagamento(reserva=reservation, valor=reservation.custo, status='p')

            reservation.quarto.save()
            reservation.save()
            payment.save()

            baseurl = f'http://{self.request.get_host()}'
            success_url = baseurl + reverse('payment_success', args=(reservation.pk,))
            cancel_url = baseurl + reverse('payment_cancel', args=(reservation.pk,))
            expires_at = int((datetime.now() + timedelta(minutes=ReservaSupport.RESERVATION_PATIENCE_MINUTES)).timestamp())

            self.logger.debug(f'success callback url: {success_url}')
            self.logger.debug(f'cancel callback url: {cancel_url}')

            prod_name = f'Reserva: Quarto Nº{reservation.quarto.numero}, classe {reservation.quarto.classe}.'
            params = {
                    'mode': 'payment',
                    'success_url': success_url,
                    'cancel_url': cancel_url,
                    'expires_at': expires_at,
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
        
            stripe_session = Session.create(**params)
            return redirect(stripe_session.url)
        
        except OperationalError:
            messages.info(request, PaymentMessages.TRANSACTION_BLOCKING)
            self.logger.critical(f'Falha na criação do pagamento: {str(e)}')
            redirect_url = request.META.get('HTTP_REFERER', reverse('quartos'))
            return redirect(redirect_url)
        
        except Exception as e:
            messages.error(request, PaymentMessages.PAYMENT_FAIL)
            self.logger.critical(f'Falha na criação do pagamento: {str(e)}')
            redirect_url = request.META.get('HTTP_REFERER', reverse('quartos'))
            return redirect(redirect_url)


def payment_success(request: HttpRequest, reservation_pk: int):
    logger = logging.getLogger('djangoLogger')
    logger.info(f'reserva {reservation_pk} recebida para sucesso de pagamento')

    payment = get_object_or_404(Pagamento, reserva__pk=reservation_pk)
    payment.reserva.status = 'F'
    payment.reserva.ativa = True
    payment.reserva.save()
    
    payment.status = 'f'
    payment.save()

    logger.debug(f'renderizando pagina de sucesso com pagamento: {payment}')
    return render(request, 'success.html', {'payment': payment})


def payment_cancel(request: HttpRequest, reservation_pk: int):
    logger = logging.getLogger('djangoLogger')
    logger.info(f'reserva {reservation_pk} recebida para cancelamento')
    try:
        payment = Pagamento.objects.get(reserva__pk=reservation_pk)
        payment.reserva.status = 'C'
        payment.reserva.ativa = False
        payment.reserva.quarto.disponivel = False
        payment.reserva.save()

        payment.status = 'c'
        payment.save()
    except Exception as e:
        logger.critical(f'nao foi possivel reverter o pagamento {payment} para a reserva {payment.reserva} : {str(e)}')

    logger.info(f'pagamento {payment} para a reserva {payment.reserva} cancelado')
    return render(request, 'cancel.html')
