from django.contrib import admin
from .models import Beneficio, Classe, Quarto, Reserva


class BeneficioAdmin(admin.ModelAdmin):
    list_display = [
        'nome',
        'descricao_curta',
        'displayable_on_homepage',
    ]
    list_editable = [
        'displayable_on_homepage',
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
    list_filter = ['hotel']
    list_editable = ['disponivel']


@admin.display(description='Status')
def status(obj):
    return obj.get_status_display().title()

class ReservaAdmin(admin.ModelAdmin):
    list_display = [
        'cliente',
        'quarto',
        'check_in',
        'checkout',
        'ativa',
        status,
    ]
    
admin.site.register(Beneficio, BeneficioAdmin)
admin.site.register(Classe, ClasseAdmin)
admin.site.register(Quarto, QuartoAdmin)
admin.site.register(Reserva, ReservaAdmin)
