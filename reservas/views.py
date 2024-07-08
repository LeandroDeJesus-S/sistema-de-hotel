from django.shortcuts import render, HttpResponse
from django.views import View
from django.core.exceptions import ValidationError

from . import validators
from .models import Classe


class Reserva(View):
    def get(self, *args, **kwargs):
        context = {
            'room_classes': Classe.objects.all(),
        }
        return render(self.request, 'reserva.html', context)
    
    def post(self, *args, **kwargs):
        NAME = self.request.POST.get('cliente-nome')
        CHECK_IN = self.request.POST.get('checkin')
        CHECKOUT = self.request.POST.get('checkout')
        QTD_ADULTS = self.request.POST.get('adultos')
        QTD_CHILDREN = self.request.POST.get('criacas')
        PHONE = self.request.POST.get('telefone')
        EMAIL = self.request.POST.get('email')
        
        # try:
        #     validators.validate_fullname(NAME)
        #     validators.validate_checkin_and_checkout(CHECK_IN, CHECKOUT)
        #     validators.validate_qtd_adultos(QTD_ADULTS)
        # except ValidationError as msg_list:
        #     print(msg_list)
        
        # print(CHECK_IN, CHECKOUT)
        return HttpResponse(self.request.POST.items())

