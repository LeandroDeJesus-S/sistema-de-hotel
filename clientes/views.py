from django.shortcuts import render, HttpResponse
from django.views import View
# Create your views here.

class Cliente(View):
    def get(self):
        return HttpResponse('Cliente GET')
    
    def get(self):
        return HttpResponse('Cliente POST')

