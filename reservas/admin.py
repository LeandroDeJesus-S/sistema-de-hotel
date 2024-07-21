from django.contrib import admin
from .models import Beneficio, Classe, Quarto, Reserva


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
        'capacidade_adultos',
        'capacidade_criancas',
        'daily_price_formatted',
        'disponivel',
        'image'
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
        'ativa',
    ]
    
admin.site.register(Beneficio, BeneficioAdmin)
admin.site.register(Classe, ClasseAdmin)
admin.site.register(Quarto, QuartoAdmin)
admin.site.register(Reserva, ReservaAdmin)
