from django.contrib import admin
from .models import Cliente, Contato


class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        'nome',
        'sobrenome',
        'nascimento',
    ]


admin.site.register(Cliente, ClienteAdmin)
admin.site.register(Contato)
