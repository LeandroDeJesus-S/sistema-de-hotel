from django.db import models
from clientes.models import Cliente
from reservas.models import Reserva
from django.core.exceptions import ValidationError


class Agendamento(models.Model):
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
        self._validate_availability_date()
                
        if self.error_messages:
            raise ValidationError(self.error_messages)
    
    def _validate_reserving_an_occupied_room(self):
        if not self.reserva.ativa:
            self.error_messages['reserva'] = 'Não é possível agendar um quarto que não esta ocupado.'
    
    def _validate_availability_date(self):
        active_for_room = Reserva.objects.get(quarto=self.reserva.quarto, ativa=True)
        if self.reserva.check_in <= active_for_room.checkout:
            self.error_messages['reserva'] = f'Data de check-in indisponível, deve ser maior que {active_for_room.checkout}'
