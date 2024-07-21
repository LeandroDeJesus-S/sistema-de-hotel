# from typing import Any
# from django.conf import settings
# from django.http import HttpRequest, HttpResponse
# from django.shortcuts import render, redirect, get_object_or_404
# from django.urls import reverse
# from django.views import View
# import stripe.stripe_object
# from reservas.models import Reserva, Quarto
# from clientes.models import Cliente
# from django.core.serializers import deserialize
# from stripe.checkout import Session
# import logging
# from datetime import datetime
# from utils.supportclass import SessionKeys
# from utils.support import clear_session_keys
# from .models import Pagamentos
# from django.db import transaction


# class Payment(View):  # TODO: retirar argumentos da url de check-in
#     def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
#         super().setup(request, *args, **kwargs)
#         self.default_return = redirect(reverse('reserva'))
#         self.logger = logging.getLogger('reservasLogger')
    
#     def get(self, _, room_id, *args, **kwargs):
#         if self.request.session.get(SessionKeys.ROOM_ID) is None:
#             self.request.session[SessionKeys.ROOM_ID] = room_id

#         reservation_id = self.request.session.get(SessionKeys.RESERVATION_ID)

#         self.logger.debug(
#             f'quarto recebido: {room_id} :: reserva recebida: {reservation_id}'
#         )
        
#         if not (reservation_id and room_id):
#             self.logger.warning('nao pode fazer checkout. redirecionando para reserva!')
#             return self.default_return
        
#         reservation = get_object_or_404(Reserva, pk__exact=int(reservation_id))
#         room = get_object_or_404(Quarto, pk__exact=int(room_id))

#         reservation_value = room.daily_price_in_cents * reservation.reservation_days / 100

#         self.logger.debug('renderizando checkout.html')
#         return render(self.request, 'checkout.html', {'reservation_value': reservation_value, 'room': room})

#     @transaction.atomic
#     def post(self, *args, **kwargs):
#         stripe.api_key = settings.STRIPE_API_KEY_SECRET

#         reservation_id = self.request.session.get(SessionKeys.RESERVATION_ID)
#         room_id = self.request.session.get(SessionKeys.ROOM_ID)

#         if not all((reservation_id, room_id)):
#             self.logger.error('id da reserva ou quarto não esta na sessão')
#             return redirect('pre_reserva')
        
#         reservation = get_object_or_404(Reserva, pk=int(reservation_id))  # processing
#         room = get_object_or_404(Quarto, pk=int(room_id))  # processing
        
#         self.logger.debug(f'reserva a ser paga: {reservation} :: quarto a ser pago: {room}')

#         reservation.reserve(room)

#         baseurl = f'http://{self.request.get_host()}'
#         success_url = baseurl + reverse('payment_success')
#         cancel_url = baseurl + reverse('payment_cancel')

#         self.logger.debug(f'success callback url: {success_url}')
#         self.logger.debug(f'cancel callback url: {cancel_url}')

#         params = {
#                 'mode': 'payment',
#                 'success_url': success_url,
#                 'cancel_url': cancel_url,
#                 'line_items': [
#                     {
#                         'adjustable_quantity': {
#                             'enabled': False,
#                         },
#                         'price_data': {
#                             'currency': 'brl',
#                             'product_data': {
#                                 'name': reservation.__str__(),
#                             }, 
#                             'unit_amount': reservation.quarto.daily_price_in_cents, 
#                         },
#                         'quantity': reservation.reservation_days
#                     }
#                 ]
#             }
        
#         try:
#             stripe_session = Session.create(**params)
#         except Exception as e:
#             return HttpResponse(str(e))
        
#         return redirect(stripe_session.url)


# @transaction.atomic
# def payment_success(request: HttpRequest):
#     logger = logging.getLogger('reservasLogger')

#     reservation_id = request.session.get(SessionKeys.RESERVATION_ID)
#     reservation = Reserva.objects.get(pk__exact=int(reservation_id))

#     reservation.quarto 
#     payment = Pagamentos.objects.create(
#         status='f',
#         valor=reservation.custo,
#         cliente=reservation.cliente,
#         reserva=reservation
#     )
    
#     log = clear_session_keys(SessionKeys.all_keys())
#     if log:
#         logger.info('session limpa com sucesso')
#     else:
#         logger.error('erro ao limpar a session')

#     return render(request, 'success.html', {'payment': payment})


# def payment_cancel(request):
#     logger = logging.getLogger('reservasLogger')

#     reservation_id = request.session.get(SessionKeys.RESERVATION_ID)
#     reservation = Reserva.objects.get(pk__exact=int(reservation_id))
#     logger.info(f'pagamento da reserva {reservation} cancelado')

#     reservation.quarto.disponivel = True
#     reservation.quarto.save()
#     logger.info(f'quarto {reservation.quarto} disponivel novamente')
#     return render(request, 'cancel.html')
