from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from clients.models import Client
from reservations.models import Reservation

from .error_messages import PaymentErrorMessages


# TODO: there is no way, I will need remodeling thins or it will be a mess
class Payment(models.Model):
    """
    Stores a single payment transaction, tracking its status and key
    identifiers from an external payment gateway.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')

    class MethodType(models.TextChoices):
        CREDIT_CARD = 'credit_card', _('Credit Card')
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        PIX = 'pix', _('Pix')
        UNKNOWN = 'unknown', _('Unknown')

    class Gateway(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        PAYPAL = 'paypal', _('PayPal')
        UNKNOWN = 'unknown', _('Unknown')

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='payments')
    reservation = models.ForeignKey(
        Reservation, on_delete=models.PROTECT, related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    payment_method_type = models.CharField(
        max_length=20, choices=MethodType.choices, default=MethodType.UNKNOWN
    )

    # --- External Gateway Information ---
    payment_gateway = models.CharField(
        max_length=20, choices=Gateway.choices, default=Gateway.UNKNOWN
    )
    gateway_customer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Customer ID from the payment gateway'),
    )
    gateway_payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Payment Intent ID from the payment gateway'),
    )
    gateway_charge_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Charge ID from the payment gateway after successful payment'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.amount != self.reservation.amount:
            raise ValidationError(PaymentErrorMessages.INVALID_PAYMENT_VALUE)

    def __str__(self):
        return f'Payment for Reservation {self.reservation.id} by {self.client}'
