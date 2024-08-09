from django.db import models
from django.core.exceptions import ValidationError
from reservations.models import Reservation
from utils.supportmodels import PaymentErrorMessages


class Payment(models.Model):
    """representa um registro de pagamento"""
    date = models.DateTimeField(
        'Data',
        auto_now_add=True,
        editable=False,
    )
    STATUS = (
        ('F', 'finalizado'),
        ('C', 'cancelado'),
        ('P', 'pendente'),
        ('PR', 'processando')
    )
    status = models.CharField(
        'Status',
        max_length=2,
        default='P',
        choices=STATUS,
    )
    amount = models.DecimalField(
        'Valor',
        max_digits=10,
        decimal_places=2
    )
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='payment_reservations',
        related_query_name='payment_reservation',
        verbose_name='Reserva'
    )
    
    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.pk}'

    def clean(self) -> None:
        super().clean()
        error_messages = {}

        if self.amount != self.reservation.amount:
            error_messages['amount'] = PaymentErrorMessages.INVALID_PAYMENT_VALUE     

        if error_messages:
            raise ValidationError(error_messages)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
