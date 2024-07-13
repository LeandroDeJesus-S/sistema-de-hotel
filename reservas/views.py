from typing import Any
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import render, HttpResponse, redirect
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
        contact = Contato.objects.filter(Q(email__exact=EMAIL)|Q(telefone__exact=PHONE)).first()
        if contact is None:
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
            messages.error(self.request, 'Por favor, escolha um quarto válido.')
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
        
        if room_id := self.request.session.get('room'):
            reservation.quarto = Quarto.objects.get(pk=room_id)
            reservation.save()
            self.request.session.update(dict(
                client_id=client.pk,
                reservation_id=reservation.pk, 
                room_class_id=room_class.pk
            ))
            self.request.session.save()
            return HttpResponse('pagina de pagamento')  # TODO: criar pagina e redirecionar

        reservation.save()
        self.request.session.update(dict(
            client_id=client.pk,
            reservation_id=reservation.pk, 
            room_class_id=room_class.pk
        ))
        self.request.session.save()
        return redirect('reserva')


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
        print('session:', self.request.session)
        print(self.request.GET.dict())
        return super().get_queryset()


class Acomodacoes(ListaQuartos):
    ...
