from django.contrib import admin
from .models import Reserva, Quarto, Beneficio, Classe


class BeneficioAdmin(admin.ModelAdmin):
    list_display = [
        'nome',
        'descricao_curta',
    ]

class ClasseAdmin(admin.ModelAdmin):
    list_display = [
        'nome',
    ]

class QuartoAdmin(admin.ModelAdmin):
    list_display = [
        'classe',
        'numero',
        'capacidade',
        'daily_price_formatted',
        'disponivel',
    ]
    list_editable = ['disponivel']

class ReservaAdmin(admin.ModelAdmin):
    list_display = [
        'cliente',
        'quarto',
        'check_in',
        'checkout',
        'qtd_adultos', 
        'qtd_criancas',
    ]
    

admin.site.register(Beneficio, BeneficioAdmin)
admin.site.register(Classe, ClasseAdmin)
admin.site.register(Quarto, QuartoAdmin)
admin.site.register(Reserva, ReservaAdmin)
