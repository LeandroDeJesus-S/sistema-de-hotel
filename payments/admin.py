from django.contrib import admin
from .models import Pagamento


class PagamentosAdmin(admin.ModelAdmin):
    list_display = [
        'cliente',
        'reserva',
        'data',
    ]


admin.site.register(Pagamento, PagamentosAdmin)
