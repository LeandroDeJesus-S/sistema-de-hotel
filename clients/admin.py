from django.contrib import admin
from .models import Client


class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        'username',
        'first_name',
        'last_name',
        'birthdate',
    ]


admin.site.register(Client, ClienteAdmin)
