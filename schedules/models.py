from django.db import models
from clients.models import Client
from reservations.models import Reservation
from django.core.exceptions import ValidationError


class Scheduling(models.Model):  # TODO: criar testes
    """
    Ao solicitar um reserva o cliente preenche os dados, os dados são validados
    o cliente sera solicitado para efetuar o pagamento e se tudo estiver de 
    acordo será criada uma task para ativar a reserva na data do agendamento e
    notificar o cliente e os ADMs via email.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)

    def clean(self):
        super().clean()
        self.error_messages = {}
        self._validate_reserving_an_occupied_room()
        self._validate_date_availability()

        if self.error_messages:
            raise ValidationError(self.error_messages)
    
    def _validate_date_availability(self):
        reservations = Reservation.objects.filter(
            room=self.reservation.room, 
            checkout__gt=self.reservation.checkin,
            checkin__lte=self.reservation.checkout,
            status__in=['A', 'S']
        )
        if not reservations.exists():
            return

        dates = Reservation.available_dates(self.reservation.room)
        self.error_messages['reservation'] = f'Data de agendamento indisponível. As datas disponíveis são: {dates}'
    
    def _validate_reserving_an_occupied_room(self):
        if not Reservation.objects.filter(room=self.reservation.room, active=True).exists():
            self.error_messages['reservation'] = 'Não é possível agendar um quarto que não esta ocupado.'
    
    def __str__(self):
        return f'{self.client} {self.reservation}'

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
