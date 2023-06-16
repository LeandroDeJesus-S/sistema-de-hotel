from django.shortcuts import render, HttpResponse
from django.views import View
from django.core.exceptions import ValidationError

from . import validators


class Reserva(View):
    def get(self, *args, **kwargs):
        return render(self.request, 'reserva.html')
    
    def post(self, *args, **kwargs):
        NAME = self.request.POST.get('nome')
        CHECK_IN = self.request.POST.get('chegada')
        CHECKOUT = self.request.POST.get('saida')
        QTD_ADULTS = self.request.POST.get('qtdAdultos')
        QTD_CHILDREN = self.request.POST.get('qtdCriacas')
        ROOM_TYPE = self.request.POST.get('tipoQuarto')
        PHONE = self.request.POST.get('telefone')
        EMAIL = self.request.POST.get('email')
        
        try:
            validators.validate_fullname(NAME)
            validators.validate_checkin_and_checkout(CHECK_IN, CHECKOUT)
            validators.validate_qtd_adultos(QTD_ADULTS)
        except ValidationError as msg_list:
            print(msg_list)
        
        print(CHECK_IN, CHECKOUT)
        return HttpResponse(self.request.POST.items())

