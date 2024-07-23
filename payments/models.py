from django.db import models
from django.core.exceptions import ValidationError
from reservas.models import Reserva
from utils.supportmodels import PaymentErrorMessages


class Pagamento(models.Model):
    data = models.DateTimeField(
        'Data',
        auto_now_add=True,
        editable=False,
    )
    STATUS = (
        ('f', 'finalizado'),
        ('c', 'cancelado'),
        ('p', 'pendente'),
        ('pr', 'processando')
    )
    status = models.CharField(
        'Status',
        max_length=2,
        default='p'
    )
    valor = models.DecimalField(
        'Valor',
        max_digits=10,
        decimal_places=2
    )
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='pagamento_reservas',
        related_query_name='pagamento_reserva',
        verbose_name='Reserva'
    )
    
    def __str__(self) -> str:
        return f'< {self.__class__.__name__}: {self.pk} >'

    def clean(self) -> None:
        super().clean()
        error_messages = {}

        if self.valor != self.reserva.custo:
            error_messages['valor'] = PaymentErrorMessages.INVALID_PAYMENT_VALUE     

        if error_messages:
            raise ValidationError(error_messages)

    class Meta:
        verbose_name = 'Pagamento'
