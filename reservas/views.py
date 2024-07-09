from typing import Any
from django.http import HttpRequest
from django.shortcuts import render, HttpResponse, redirect
from datetime import datetime
from django.urls import reverse
from django.contrib import messages
from django.views import View
from django.views.generic.list import ListView
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Classe, Reserva, Quarto
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
        return render(self.request, self.template_name, self.context)
    
    def post(self, *args, **kwargs):
        self.context['req'] = self.request
        NAME = self.request.POST.get('cliente_nome').split(maxsplit=1)
        if len(NAME) < 2:
            messages.error(self.request, 'Nome inválido')
            return render(self.request, self.template_name, self.context)
        
        firstname, lastname = NAME
        client = Cliente.objects.filter(nome__iexact=firstname, sobrenome__iexact=lastname).first()
        if client is None:
            client = Cliente(
                nome=firstname, 
                sobrenome=lastname,
            )

            if (error_msg := validate_model(client)):
                {messages.error(self.request, msg) for msg in error_msg}
                return render(self.request, self.template_name, self.context)
            
            client.save()
        
        PHONE = self.request.POST.get('telefone')
        EMAIL = self.request.POST.get('email')
        if Contato.objects.filter(Q(email__exact=EMAIL)|Q(telefone__exact=PHONE)).exists():
            messages.error(self.request, 'E-mail ou telefone ja existe')
            return render(self.request, self.template_name, self.context)
        
        contact = Contato(
            email=EMAIL,
            telefone=PHONE,
            cliente=client
        )
        if (error_msg := validate_model(contact)):
            {messages.error(self.request, msg) for msg in error_msg}
            return render(self.request, self.template_name, self.context)
        
        contact.save()

        CHECK_IN = datetime.strptime(self.request.POST.get('checkin', '0000-00-00'), '%Y-%m-%d')
        CHECKOUT = datetime.strptime(self.request.POST.get('checkout', '0000-00-00'), '%Y-%m-%d')

        QTD_ADULTS = self.request.POST.get('adultos')
        QTD_CHILDREN = self.request.POST.get('criancas')

        ROOM_CLASS_ID = self.request.POST.get('quarto', 0)
        room_class = Classe.objects.filter(pk__exact=int(ROOM_CLASS_ID)).first()
        if room_class is None:
            messages.error(self.request, 'Por favor, escolha um quarto.')
            return render(self.request, self.template_name, self.context)

        reservation = Reserva(
            check_in=CHECK_IN, 
            checkout=CHECKOUT, 
            qtd_adultos=QTD_ADULTS,
            qtd_criancas=QTD_CHILDREN,
            cliente=client
        )
        if (error_msg := validate_model(reservation)):
            {messages.error(self.request, msg) for msg in error_msg}
            return render(self.request, self.template_name, self.context)

        reservation.save()
        return redirect(
            'reserva', 
            client_id=client.pk,
            reservation_id=reservation.pk, 
            room_class_id=room_class.pk
        )


class ListRooms(ListView):
    model = Quarto
    template_name = 'reserva.html'
    context_object_name = 'rooms_available'
    

class Reservas(View):
    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)
        self.template_name = 'reserva.html'
        self.context = {}

    def get(self, request):#, client_id, reservation_id, room_class_id, *args, **kwargs):
        return render(request, self.template_name, self.context)
    
    def post(self, *args, **kwargs):
        return HttpResponse('')
