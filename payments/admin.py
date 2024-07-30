from django.contrib import admin
from .models import Payment


class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'reservation',
        'date',
        'amount',
        'status'
    ]


admin.site.register(Payment, PaymentAdmin)
