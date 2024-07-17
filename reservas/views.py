from typing import Any, Tuple, List, Dict
from pprint import pprint
import logging
import logging as log
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers import serialize, deserialize
from datetime import datetime
from django.urls import reverse
from django.contrib import messages
from django.views import View
from django.views.generic.list import ListView
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Classe, Reserva, Quarto, Beneficio
from .validators import validate_model, convert_date
from clientes.models import Cliente, Contato


class PreReserva(View):
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('reservasLogger')
        self.context = {
            'room_classes': Classe.objects.all(),
        }
        self.template_name = 'prereserva.html'
        self._last_room_id = None

    def get(self, *args, **kwargs):
        room_id_arg = self.request.GET.get('room_id')
        room_id_session = self.request.session.get('room_id')
        same_room_ids = room_id_arg == room_id_session
        both_args = room_id_arg and room_id_session
        self.logger.debug(f'room_id_arg={room_id_arg} :: room_id_session={room_id_session} :: same_room_ids={same_room_ids}')
        
        if room_id_arg and not room_id_session:
            self.request.session['room_id'] = room_id_arg
            self.logger.debug(f'added room_id_arg={room_id_arg} to session')

        elif not room_id_arg and room_id_session:
            del self.request.session['room_id']
            self.logger.debug(f'deleted room_id_session={room_id_session}')

        elif both_args and not same_room_ids:
            self.request.session['room_id'] = room_id_arg
            self.logger.debug(f'updated session to room_id_arg={room_id_arg}')

        elif both_args and same_room_ids:
            del self.request.session['room_id']
            self.logger.debug(f'repeated ids deleted {room_id_arg} and {room_id_session}')
        
        self.request.session.save()
        self.logger.debug(f'room_id {room_id_arg} arg salvo na session')
        # if room_id := self.request.GET.get('room_id'):
        #     if self.request.session.get('room_id'):
        #         self.request.session['room_id'] = room_id
        #     else:
        #         same_room_id = room_id == self.request.session['room_id']
        #         if same_room_id:
        #             del self.request.session['room_id']
        #         else:
        #             self.request.session['room_id'] = room_id


        self.logger.debug('renderizando template para pré-reserva')
        return render(self.request, self.template_name, self.context)
    
    def post(self, *args, **kwargs):
        client = self._process_client()
        if client is None:
            return render(self.request, self.template_name, self.context)
        
        contact = self._process_contact(client)
        if contact is None:
            return render(self.request, self.template_name, self.context)
        
        reservation_room = self._process_reservation()
        if reservation_room is None:
            return render(self.request, self.template_name, self.context)
        
        reservation, room_class = reservation_room

        # solicitação de reserva sem pre-reserva
        if room_id := self.request.session.get('room_id'):
            self.logger.debug('pegando room_id da sessão')

            reservation_json = serialize('json', [reservation])
            self.logger.debug(f'reserva realizada = {reservation}')

            self.request.session['reservation'] = reservation_json
            self.request.session.save()
            self.logger.debug(f'reserva salva na sessão :: redirecionando para pagamento.')
            return redirect(reverse('payment', args=(room_id, client.pk)))

        self.request.session['client_id'] = client.pk
        self.request.session['room_class_id'] = room_class.pk
        self.request.session.save()
        return redirect('reserva')

    def _process_client(self) -> Cliente|None:
        self.logger.debug('processando dados do cliente')

        NAME = self.request.POST.get('cliente_nome')
        LASTNAME = self.request.POST.get('cliente_sobrenome')
        BIRTHDAY = convert_date(self.request.POST.get('cliente_nascimento', '0001-01-01'))
        
        client = Cliente.objects.filter(
            nome__iexact=NAME, 
            sobrenome__iexact=LASTNAME, 
            nascimento__exact=BIRTHDAY
        ).first()
        self.logger.debug(f'Cliente já existe: {bool(client)}')
        if client is None:
            self.logger.debug('criando novo cliente')
            client = Cliente(
                nome=NAME, 
                sobrenome=LASTNAME,
                nascimento=BIRTHDAY
            )
            if (error_msg := validate_model(client)):
                messages.error(self.request, error_msg)
                self.logger.error(f'cliente não criado: {error_msg}')
                return None
            
            client.save()
            self.logger.debug(f'novo cliente registrado: {client}')
        
        self.request.session['client_id'] = client.pk
        return client

    def _process_contact(self, client) -> Contato|None:
        self.logger.debug('processando dados de contato')

        PHONE = self.request.POST.get('telefone')
        EMAIL = self.request.POST.get('email')
        contact = Contato.objects.filter(Q(email__exact=EMAIL)|Q(telefone__exact=PHONE)).first()
        self.logger.debug(f'contato já existe: {bool(contact)}')
        if contact is None:
            self.logger.debug('criando novo contato')
            contact = Contato(
                email=EMAIL,
                telefone=PHONE,
                cliente=client
            )
            if (error_msg := validate_model(contact)):
                messages.error(self.request, error_msg)
                self.logger.debug(f'erro ao criar contato: {error_msg}')
                return None
            
            contact.save()
            self.logger.debug(f'contato criado com successo: {contact}')
        return contact

    def _process_reservation(self) -> Tuple[Reserva, Classe]|None:
        self.logger.debug('processando dados de reserva')

        CHECK_IN =convert_date(self.request.POST.get('checkin', '0001-01-01'))
        CHECKOUT =convert_date(self.request.POST.get('checkout', '0001-01-01'))

        QTD_ADULTS = self.request.POST.get('adultos')
        QTD_CHILDREN = self.request.POST.get('criancas')

        session_room_id = self.request.session.get('room_id')  # 
        if session_room_id:
            room_class = get_object_or_404(Quarto, pk=session_room_id).classe
            self.logger.debug(f'quarto class {room_class.pk} recuperado usando id do quarto fornecido diretamente')

        else:
            self.logger.debug('pegando classe de quarto via form de pré-reserva')
            ROOM_CLASS_ID = self.request.POST.get('quarto')
            if (ROOM_CLASS_ID == '0') or (ROOM_CLASS_ID is None):
                messages.error(self.request, 'Por favor, escolha um quarto válido.')
                self.logger.debug('usuário não informou um quarto válido')
                return None

            room_class = Classe.objects.filter(pk__exact=int(ROOM_CLASS_ID)).first()
            self.logger.debug(f'classe de quarto recuperado: {room_class}')
        
        OBS = self.request.POST.get('obs', '')

        reservation = Reserva(
            check_in=CHECK_IN, 
            checkout=CHECKOUT, 
            qtd_adultos=QTD_ADULTS,
            qtd_criancas=QTD_CHILDREN,
            observacoes=OBS,
            status='p'
        )
        self.logger.debug(f'dados de pré-reserva: {reservation}')
        if (error_msg := validate_model(reservation, exclude=['cliente'])):
            messages.error(self.request, error_msg)
            self.logger.debug(f'erro ao salvar reserva: {error_msg}')
            return None

        self.logger.debug(f'reserva processada: {reservation.pk} :: classe do quarto: {room_class}')
        return reservation, room_class


class ListaQuartos(ListView):
    logger = logging.getLogger('reservasLogger')

    model = Quarto
    template_name = 'reserva.html'
    context_object_name = 'rooms_available'
    ordering = '-preco_diaria'
    

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['benefits'] = Beneficio.objects.all()
        self.logger.debug('add benefits para o context')
        return context
    
    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        room_class_id = self.request.session.get('room_class_id')
        self.logger.debug(f'classe capiturada via session: {room_class_id}')
        if room_class_id is None:
            return qs
        
        room_class = Classe.objects.get(pk__exact=room_class_id)
        
        self.logger.debug(f'classe capturada via session: {room_class.pk}')
        self.logger.debug(f'session: {self.request.session}')
        return qs.filter(classe__exact=room_class)


class Acomodacoes(ListaQuartos):
    ...
