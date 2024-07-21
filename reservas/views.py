# from typing import Any
import logging
# from django.db.models.query import QuerySet
# from django.http import HttpRequest, HttpResponseServerError
# from django.shortcuts import render, HttpResponse, redirect, get_object_or_404, HttpResponseRedirect
from django.urls import reverse
# from django.contrib import messages
# from django.views import View
from django.views.generic.list import ListView
# from django.db.models import Q
# from django.db import transaction

from .models import Quarto, Beneficio
# from .validators import validate_model, convert_date
# from clientes.models import Cliente
# from utils.supportclass import SessionKeys, ReservaErrorMessages
# from utils.support import clear_session_keys
# from pprint import pprint


# class PreReserva(View):
#     def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
#         super().setup(request, *args, **kwargs)
#         self.logger = logging.getLogger('reservasLogger')
#         self.context = {
#             'room_classes': Classe.objects.all(),
#         }
#         self.template_name = 'prereserva.html'
#         self._last_room_id = None

#     def get(self, *args, **kwargs):
#         # self.logger.debug(f'referer: {self.request.META.get("HTTP_REFERER")}')
#         # self.logger.debug(f'session: {self.request.session.items()}')

#         # room_id_query_param = self.request.GET.get('room_id')
#         # room_id_session = self.request.session.get('room_id')

#         # same_room_ids = room_id_query_param == room_id_session

#         # self.logger.debug(
#         #     f'room_id_arg={room_id_query_param} ::\
#         #     room_id_session={room_id_session} :: \
#         #     same_room_ids={same_room_ids}'
#         # )

#         # # usuário veio pela pagina de acomodações clicando no botão 'reservar'
#         # if room_id_query_param and not room_id_session:
#         #     self.request.session[SessionKeys.ROOM_ID] = room_id_query_param
#         #     self.request.session.save()
#         #     self.logger.debug(f'room_id_arg={room_id_query_param} salvo na session')
#         #     self.logger.debug(f'current session: {self.request.session.items()}')

#         # # usuário veio por 'acomodacoes' porem não concluiu o form saiu e voltou
#         # elif not room_id_query_param and room_id_session:
#         #     del self.request.session[SessionKeys.ROOM_ID]
#         #     self.request.session.save()
#         #     self.logger.debug(f'deleted room_id_session={room_id_session}')
#         #     self.logger.debug(f'current session: {self.request.session.items()}')

#         # self.logger.debug('renderizando template para pre-reserva')
#         return render(self.request, self.template_name, self.context)
    
#     # def post(self, *args, **kwargs):
#     #     client = self._process_client()
#     #     if isinstance(client, HttpResponse):
#     #         return client
        
#     #     contact = self._process_contact(client)
#     #     if isinstance(contact, HttpResponse):
#     #         return contact
        
#     #     reservation = self._process_reservation(client)
#     #     if isinstance(reservation, HttpResponseRedirect|HttpResponse):
#     #         return reservation
        
#     #     elif isinstance(reservation, HttpResponse):
#     #         return render(self.request, self.template_name, self.context)
        
#     #     elif not isinstance(reservation, Reserva):
#     #         return HttpResponseServerError('Erro inesperado ao processar reserva')

#     def _process_client(self) -> Cliente|HttpResponse:
#         """realiza o processamento relacionado a model Cliente.

#         Returns:
#             Cliente: caso tudo ocorra como esperado.
#             HttpResponse: caso um render() seja retornado.
#         """
#         self.logger.debug('processando dados do cliente')

#         NAME = self.request.POST.get('cliente_nome')
#         LASTNAME = self.request.POST.get('cliente_sobrenome')
#         BIRTHDAY = convert_date(self.request.POST.get('cliente_nascimento', '0001-01-01'))
        
#         client = Cliente.objects.filter(
#             nome__iexact=NAME, 
#             sobrenome__iexact=LASTNAME, 
#             nascimento__exact=BIRTHDAY
#         ).first()
#         self.logger.debug(f'cliente ja existe: {bool(client)}')
#         if client is None:
#             self.logger.debug('criando novo cliente')
#             client = Cliente(
#                 nome=NAME, 
#                 sobrenome=LASTNAME,
#                 nascimento=BIRTHDAY
#             )
#             if (error_msg := validate_model(client)):
#                 messages.error(self.request, error_msg)
#                 self.logger.error(f'cliente não criado: {error_msg}')
#                 return render(self.request, self.template_name, self.context)
            
#             client.save()
#             self.logger.debug(f'novo cliente registrado: {client}')
        
#         self.request.session[SessionKeys.CLIENT_ID] = client.pk
#         self.request.session.save()
#         return client

#     def _process_contact(self, client: Cliente) -> HttpResponse:
#         """realiza o processamento da model Contato

#         Args:
#             client (Cliente): instancia da model Cliente

#         Returns:
#             Contato: caso tudo ocorra como esperado
#             HttpResponse: caso um render() seja retornado
#         """
#         self.logger.debug('processando dados de contato')

#         PHONE = self.request.POST.get('telefone', '')
#         EMAIL = self.request.POST.get('email', '')

#         contact = Contato.objects.filter(cliente=client).first()

#         self.logger.debug(f'cliente ja possui um contato salvo: {bool(contact)}')

#         if contact is None:
#             self.logger.debug('criando novo contato')
#             contact = Contato(
#                 email=EMAIL,
#                 telefone=PHONE,
#                 cliente=client
#             )
#             if (error_msg := validate_model(contact)):
#                 messages.error(self.request, error_msg)
#                 self.logger.debug(f'erro ao criar contato: {error_msg}')
#                 return render(self.request, self.template_name, self.context)
            
#             contact.save()
#             self.logger.debug(f'contato criado com sucesso: {contact}')
        
#         else:
#             if contact.telefone != PHONE:
#                 contact.telefone = PHONE
#                 self.logger.debug(f'telefone para cliente {client.pk} atualizado')

#             if contact.email != EMAIL:
#                 contact.email = EMAIL
#                 self.logger.debug(f'email para cliente {client.pk} atualizado')
            
#             contact.save()
#             self.logger.debug('usando contato ja salvo')
        
#         return contact

#     @transaction.atomic
#     def _process_reservation(self, client: Cliente) -> Reserva|HttpResponseRedirect|HttpResponse:
#         """realiza o processamento da model Reserva

#         Args:
#             client (Cliente): instancia processada do cliente

#         Returns:
#             Reserva: caso tudo ocorra como esperado.
#             HttpResponseRedirect: caso um redirect() seja retornado
#             HttpResponse: caso um render() seja retornado
#         """
#         self.logger.debug('processando dados de reserva')

#         CHECK_IN = convert_date(self.request.POST.get('checkin', '0001-01-01'))
#         CHECKOUT = convert_date(self.request.POST.get('checkout', '0001-01-01'))

#         QTD_ADULTS = self.request.POST.get('adultos')
#         QTD_CHILDREN = self.request.POST.get('criancas')

#         OBS = self.request.POST.get('obs', '')

#         reservation = Reserva(
#             check_in=CHECK_IN, 
#             checkout=CHECKOUT, 
#             qtd_adultos=QTD_ADULTS,
#             qtd_criancas=QTD_CHILDREN,
#             observacoes=OBS,
#             cliente=client
#         )

        
#         session_room_id = self.request.session.get(SessionKeys.ROOM_ID)
#         if session_room_id:  # pegando quarto via session se cliente veio da pagina de acomodações
#             self.request.session[SessionKeys.RESERVATION_ID] = reservation.pk
#             self.request.session.save()
#             return redirect(reverse('payment', args=(session_room_id,)))

#         self.logger.debug('pegando classe de quarto via form de pre-reserva')

#         ROOM_CLASS_ID = self.request.POST.get('quarto')
#         if (ROOM_CLASS_ID == '0') or (ROOM_CLASS_ID is None):
#             messages.error(self.request, ReservaErrorMessages.INVALID_ROOM_CHOICE)
#             self.logger.debug('usuário não informou um quarto válido')
#             return render(self.request, self.template_name, self.context)

#         self.request.session[SessionKeys.ROOM_CLASS_ID] = ROOM_CLASS_ID
#         self.logger.debug(f'classe de quarto {ROOM_CLASS_ID} adicionada na session')

#         self.logger.debug(f'validando reserva')
#         if (error_msg := validate_model(reservation)):
#             messages.error(self.request, error_msg)
#             self.logger.debug(f'erro ao salvar reserva: {error_msg}')
#             return render(self.request, self.template_name, self.context)

#         reservation.save()

#         self.request.session[SessionKeys.RESERVATION_ID] = reservation.pk
#         self.request.session.save()

#         self.logger.debug(f'reserva processada: {reservation.pk} :: classe do quarto: {ROOM_CLASS_ID}')
#         return redirect('reserva')


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
    
    # def get_queryset(self) -> QuerySet[Any]:
    #     referer = self.request.META.get("HTTP_REFERER", '')

    #     self.logger.debug(f'referer: {referer}')
    #     self.logger.debug(f'session: {self.request.session.items()}')

    #     if self.request.session.has_key(SessionKeys.ROOM_ID) and reverse('pre_reserva') not in referer:
    #         log = clear_session_keys(
    #             self.request.session,
    #             SessionKeys.all_keys(exclude=['CLIENT_ID'])
    #         )

    #         self.logger.debug(f'session keys deleted: {log}')
    #         self.logger.debug(f'current session: {self.request.session.items()}')

    #         reservation = Reserva.objects.filter(pk__exact=SessionKeys.RESERVATION_ID).first()
    #         if reservation is not None: 
    #             deleted = reservation.delete()
    #             self.logger.debug(f'reservation deleted: {deleted}')

    #     qs = super().get_queryset()
    #     room_class_id = self.request.session.get(SessionKeys.ROOM_CLASS_ID)
    #     self.logger.debug(f'classe capturada via session: {room_class_id}')
    #     if room_class_id:
    #         qs = qs.filter(classe__pk=int(room_class_id))
        
    #     reservation_id = self.request.session.get(SessionKeys.RESERVATION_ID)
    #     self.logger.debug(f'reserva capturada via session: {reservation_id}')
    #     if reservation_id:
    #         reservation = get_object_or_404(Reserva, pk__exact=int(reservation_id))
    #         qs = qs.filter(
    #             capacidade_criancas__gte=reservation.qtd_criancas,
    #             capacidade_adultos__gte=reservation.qtd_adultos,
    #         )        
        
    #     return qs
