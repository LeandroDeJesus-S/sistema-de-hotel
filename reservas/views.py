from typing import Any, Tuple, List, Dict
from pprint import pprint
import logging as log
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import render, HttpResponse, redirect
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
from .validators import validate_model
from clientes.models import Cliente, Contato


class PreReserva(View):
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.context = {
            'room_classes': Classe.objects.all(),
        }
        self.template_name = 'prereserva.html'

    def get(self, *args, **kwargs):
        if room_id := self.request.GET.get('room'):
            self.request.session['room_id'] = room_id
            self.request.session.save()

        return render(self.request, self.template_name, self.context)
    
    def post(self, *args, **kwargs):
        pprint(self.request.POST.dict())
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
        
        
        # solicitação de reserva diretamente de acomodações
        if room_id := self.request.session.get('room'):
            reservation.quarto = Quarto.objects.get(pk__exact=room_id)
            data = serialize('json', [reservation, room_class])
            self.request.session['pre_reserva'] = data
            self.request.session.save()
            return HttpResponse(f'Cliente {client.pk} reservou quarto {reservation.quarto}')  # TODO: criar pagina e redirecionar

        data = serialize('json', [reservation, room_class])
        self.request.session['pre_reserva'] = data
        self.request.session.save()
        return redirect('reserva')

    def _process_client(self) -> Cliente|None:
        NAME = self.request.POST.get('cliente_nome')
        print('_process_client', NAME)
        LASTNAME = self.request.POST.get('cliente_sobrenome')
        BIRTHDAY = self.request.POST.get('cliente_nascimento')
        
        client = Cliente.objects.filter(
            nome__iexact=NAME, 
            sobrenome__iexact=LASTNAME, 
            nascimento__exact=BIRTHDAY
        ).first()
        if client is None:
            client = Cliente(
                nome=NAME, 
                sobrenome=LASTNAME,
                nascimento=BIRTHDAY
            )
            if (error_msg := validate_model(client)):
                messages.error(self.request, error_msg)
                return None
            
            client.save()
            
        return client

    def _process_contact(self, client) -> Contato|None:
        PHONE = self.request.POST.get('telefone')
        EMAIL = self.request.POST.get('email')
        contact = Contato.objects.filter(Q(email__exact=EMAIL)|Q(telefone__exact=PHONE)).first()
        if contact is None:
            contact = Contato(
                email=EMAIL,
                telefone=PHONE,
                cliente=client
            )
            if (error_msg := validate_model(contact)):
                messages.error(self.request, error_msg)
                return None
            
            contact.save()

        return contact

    def _process_reservation(self) -> Tuple[Reserva, Classe]|None:
        CHECK_IN = datetime.strptime(self.request.POST.get('checkin', '0000-00-00'), '%Y-%m-%d')
        CHECKOUT = datetime.strptime(self.request.POST.get('checkout', '0000-00-00'), '%Y-%m-%d')

        QTD_ADULTS = self.request.POST.get('adultos')
        QTD_CHILDREN = self.request.POST.get('criancas')

        ROOM_CLASS_ID = self.request.POST.get('quarto', 0)
        room_class = Classe.objects.filter(pk__exact=int(ROOM_CLASS_ID)).first()
        if room_class is None:
            messages.error(self.request, 'Por favor, escolha um quarto válido.')
            return None
        
        OBS = self.request.POST.get('obs', '')

        reservation = Reserva(
            check_in=CHECK_IN, 
            checkout=CHECKOUT, 
            qtd_adultos=QTD_ADULTS,
            qtd_criancas=QTD_CHILDREN,
            observacoes=OBS,
            status='p'
        )
        
        if (error_msg := validate_model(reservation, exclude=['cliente'])):
            messages.error(self.request, error_msg)
            log.debug(error_msg)
            return None

        return reservation, room_class


class ListaQuartos(ListView):
    model = Quarto
    template_name = 'reserva.html'
    context_object_name = 'rooms_available'
    ordering = '-preco_diaria'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['benefits'] = Beneficio.objects.all()
        return context
    
    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        data = self.request.session.get('pre_reserva')
        if data is None:
            return qs
        
        _, room_class = list(deserialize('json', data))
        return qs.filter(classe__exact=room_class.object)


class Acomodacoes(ListaQuartos):
    ...


class Payments(View):
    def setup(self, *args: Any, **kwargs: Any) -> None:
        super().setup(*args, **kwargs)
        self.template_name = 'payments.html'
    
    def get(self, *args, **kwargs):
        return render(self.request, self.template_name)
