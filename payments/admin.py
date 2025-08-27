from django.contrib import admin

from .models import Payment


class PaymentAdmin(admin.ModelAdmin):
    list_display = ['client', 'room', 'date', 'amount', 'status']

    @admin.display(description='Cliente')
    def client(self, obj):  # noqa: PLR6301
        return obj.reservation.client

    @admin.display(description='Quarto')
    def room(self, obj):  # noqa: PLR6301
        return obj.reservation.room.number


admin.site.register(Payment, PaymentAdmin)
