from django.contrib import admin
from .models import Cliente


class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        'username',
        'nome',
        'sobrenome',
        'nascimento',
    ]


admin.site.register(Cliente, ClienteAdmin)
