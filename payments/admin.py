from django.contrib import admin
from django.utils.translation import gettext_lazy as gtl

from .models import Payment


class PaymentAdmin(admin.ModelAdmin):
    list_display = ['client', 'room', 'created_at', 'updated_at', 'status']
    readonly_fields = list_display

    @admin.display(description=gtl('Cliente'))
    def client(self, obj):  # noqa: PLR6301
        return obj.reservation.client

    @admin.display(description=gtl('Quarto'))
    def room(self, obj):  # noqa: PLR6301
        return obj.reservation.room.number


admin.site.register(Payment, PaymentAdmin)
