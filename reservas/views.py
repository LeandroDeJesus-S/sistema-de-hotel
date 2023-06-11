from django.shortcuts import render, HttpResponse
from django.views import View


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
        return HttpResponse(self.request.POST.items())
        
