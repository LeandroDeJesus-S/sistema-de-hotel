from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as gtl

from clients.models import Client
from reservations.domain.value_objects import Currency
from reservations.models import Reservation

from .error_messages import PaymentErrorMessages
from .rules import PaymentRules


# TODO: there is no way, I will need remodeling thins or it will be a mess
class Payment(models.Model):
    """
    Stores a single payment transaction, tracking its status and key
    identifiers from an external payment gateway.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', gtl('Pendente')
        COMPLETED = 'completed', gtl('Concluído')
        FAILED = 'failed', gtl('Falhou')
        REFUNDED = 'refunded', gtl('Reembolsado')
        CANCELLED = 'cancelled', gtl('Cancelado')

    class MethodType(models.TextChoices):
        CREDIT_CARD = 'credit_card', gtl('Cartão de Crédito')
        BANK_TRANSFER = 'bank_transfer', gtl('Transferência Bancária')
        PIX = 'pix', gtl('Pix')
        UNKNOWN = 'unknown', gtl('Desconhecido')

    class Gateway(models.TextChoices):
        STRIPE = 'stripe', gtl('Stripe')
        PAYPAL = 'paypal', gtl('PayPal')
        UNKNOWN = 'unknown', gtl('Desconhecido')

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text=gtl('Cliente que realizou o pagamento'),
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text=gtl('Reserva associada ao pagamento'),
    )
    currency = models.CharField(
        gtl('Currency'),
        max_length=10,
        choices=[(tag.value, tag.name) for tag in Currency],
        default=Currency.USD.value,
        null=True,
        blank=True,
        help_text=gtl('Currency for the payment'),
    )
    price = models.PositiveIntegerField(
        gtl('Price'),
        null=True,
        blank=True,
        help_text=gtl('Payment price in cents'),
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=gtl('Status atual do processamento do pagamento'),
    )
    payment_method_type = models.CharField(
        max_length=PaymentRules.METHOD_TYPE_MAX_LEN,
        choices=MethodType.choices,
        default=MethodType.UNKNOWN,
        help_text=gtl('Tipo de método de pagamento utilizado (máximo %(max)s caracteres)')
        % {'max': PaymentRules.METHOD_TYPE_MAX_LEN},
    )

    # --- External Gateway Information ---
    payment_gateway = models.CharField(
        max_length=PaymentRules.GATEWAY_MAX_LEN,
        choices=Gateway.choices,
        default=Gateway.UNKNOWN,
        help_text=gtl('Gateway de pagamento usado (ex: Stripe) (máximo %(max)s caracteres)')
        % {'max': PaymentRules.GATEWAY_MAX_LEN},
    )
    gateway_customer_id = models.CharField(
        max_length=PaymentRules.GATEWAY_FIELD_MAX_LEN,
        null=True,
        blank=True,
        db_index=True,
        help_text=gtl('ID do cliente no gateway de pagamento (máximo %(max)s caracteres)')
        % {'max': PaymentRules.GATEWAY_FIELD_MAX_LEN},
    )
    gateway_payment_intent_id = models.CharField(
        max_length=PaymentRules.GATEWAY_FIELD_MAX_LEN,
        null=True,
        blank=True,
        db_index=True,
        help_text=gtl('ID da intenção de pagamento no gateway (máximo %(max)s caracteres)')
        % {'max': PaymentRules.GATEWAY_FIELD_MAX_LEN},
    )
    gateway_payment_session_id = models.CharField(
        max_length=PaymentRules.GATEWAY_FIELD_MAX_LEN,
        null=True,
        blank=True,
        db_index=True,
        help_text=gtl('ID da sessão de pagamento no gateway (máximo %(max)s caracteres)')
        % {'max': PaymentRules.GATEWAY_FIELD_MAX_LEN},
    )
    gateway_charge_id = models.CharField(
        max_length=PaymentRules.GATEWAY_FIELD_MAX_LEN,
        null=True,
        blank=True,
        db_index=True,
        help_text=gtl(
            'ID da cobrança no gateway após o pagamento bem-sucedido '
            '(máximo %(max)s caracteres)'
        )
        % {'max': PaymentRules.GATEWAY_FIELD_MAX_LEN},
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text=gtl('Data e hora da criação do pagamento')
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text=gtl('Última atualização do status do pagamento')
    )
    refunded_currency = models.CharField(
        gtl('Refunded Currency'),
        max_length=10,
        choices=[(tag.value, tag.name) for tag in Currency],
        null=True,
        blank=True,
        default=None,
        help_text=gtl('Currency of the refund'),
    )
    refunded_price = models.PositiveIntegerField(
        gtl('Refunded Price'),
        null=True,
        blank=True,
        help_text=gtl('Refunded price in cents'),
    )
    refunded_at = models.DateTimeField(
        null=True, blank=True, help_text=gtl('Data e hora do reembolso')
    )
    refund_reason = models.TextField(
        blank=True, help_text=gtl('Motivo do reembolso, se realizado')
    )

    def clean(self):
        super().clean()
        if self.price != self.reservation.price:
            raise ValidationError(PaymentErrorMessages.INVALID_PAYMENT_VALUE)

    def __str__(self):
        return f'Payment for Reservation {self.reservation.id} by {self.client}'
