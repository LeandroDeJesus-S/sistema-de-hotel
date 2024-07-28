from django.db import models
from clientes.models import Cliente
from reservas.models import Reserva
from django.core.exceptions import ValidationError


class Agendamento(models.Model):  # TODO: criar testes
    """
    Ao solicitar um reserva o cliente preenche os dados, os dados são validados
    o cliente sera solicitado para efetuar o pagamento e se tudo estiver de 
    acordo será criada uma task para ativar a reserva na data do agendamento e
    notificar o cliente e os ADMs via email.
    """
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)

    def clean(self):
        super().clean()
        self.error_messages = {}
        self._validate_reserving_an_occupied_room()
        self._validate_date_availability()

        if self.error_messages:
            raise ValidationError(self.error_messages)
    
    def _validate_date_availability(self):
        reservas = Reserva.objects.filter(
            quarto=self.reserva.quarto, 
            checkout__gt=self.reserva.check_in,
            check_in__lte=self.reserva.checkout,
            status__in=['A', 'S']
        )
        if not reservas.exists():
            return

        dates = Reserva.available_dates(self.reserva.quarto)
        self.error_messages['reserva'] = f'Data de agendamento indisponível. {dates}+'
    
    def _validate_reserving_an_occupied_room(self):
        if not Reserva.objects.filter(quarto=self.reserva.quarto, ativa=True).exists():
            self.error_messages['reserva'] = 'Não é possível agendar um quarto que não esta ocupado.'
    
    # def _validate_availability_date(self):
    #     reservation = Reserva.objects.filter(quarto=self.reserva.quarto, status__in=['A', 'S']).latest('checkout')
    #     if reservation and  self.reserva.check_in < reservation.checkout:
    #         self.error_messages['reserva'] = f'Data de check-in indisponível, deve ser a partir de {reservation.checkout}'

    def __str__(self):
        return f'{self.cliente} {self.reserva}'
