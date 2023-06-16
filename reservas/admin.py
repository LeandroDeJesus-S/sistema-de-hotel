from django.contrib import admin
from .models import Reserva


class ReservaAdmin(admin.ModelAdmin):
    list_display = [
        'nome', 'check_in', 'checkout', 'quantidade_de_adultos', 
        'quantidade_de_criancas', 'tipo_de_quarto'
    ]
    
    
admin.site.register(Reserva, ReservaAdmin)
