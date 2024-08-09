from django.db import models
from clients.models import Client
from reservations.models import Reservation
from django.core.exceptions import ValidationError


class Scheduling(models.Model):
    """entidade que relaciona o agendamento de uma reserva
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)

    def clean(self):
        super().clean()
        self.error_messages = {}
        self._validate_scheduling_an_occupied_room()
        self._validate_date_availability()

        if self.error_messages:
            raise ValidationError(self.error_messages)
    
    def _validate_date_availability(self):
        """valida se as datas de check-in e check-out se sobrepõem
        com reservas ativas ou agendadas para o mesmo quarto"""
        self.reservation._validate_date_availability(self.error_messages, 'reservation')

    def _validate_scheduling_an_occupied_room(self):
        """valida se o agendamento é para um quarto ocupado"""
        if not Reservation.objects.filter(room=self.reservation.room, active=True).exists():
            self.error_messages['reservation'] = 'Não é possível agendar um quarto que não esta ocupado.'
    
    def __str__(self):
        return f'{self.client} {self.reservation}'

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
