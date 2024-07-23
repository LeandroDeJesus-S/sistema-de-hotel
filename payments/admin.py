from django.contrib import admin
from .models import Pagamento


class PagamentosAdmin(admin.ModelAdmin):
    list_display = [
        'reserva',
        'data',
        'valor',
        'status'
    ]


admin.site.register(Pagamento, PagamentosAdmin)
