from datetime import datetime, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.management import call_command

from schedules.models import Scheduling
from reservations.models import Reservation
from clients.models import Client


class TestScheduling(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')
        self.user = Client.objects.get(pk=1)
        self.reservation = Reservation.objects.filter(client=self.user, room__pk=2).first()
        self.other_reservation = Reservation.objects.filter(
            room=self.reservation.room
        ).exclude(client=self.user).first()
    
    def test_validate_date_availability(self):
        """testa se a função _validate_date_availability levanta
        validation error caso a data do agendamento não esteja disponível
        """
        self.other_reservation.checkin = self.reservation.checkin
        self.other_reservation.status = 'A'
        self.other_reservation.active = True
        self.other_reservation.save()

        sch = Scheduling(client=self.user, reservation=self.reservation)
        sch.error_messages = {}
        with self.assertRaises(ValidationError):
            sch._validate_date_availability()
            if sch.error_messages:
                raise ValidationError(sch.error_messages)
    
    def test_validate_scheduling_an_occupied_room(self):
        """testa se a função _validate_scheduling_an_occupied_room levanta
        validation error caso o quarto do agendamento não esteja com reserva ativa
        """
        for r in Reservation.objects.filter(room=self.reservation.room):
            r.status = 'F'
            r.active = False
            r.save()

        sch = Scheduling(client=self.user, reservation=self.reservation)
        sch.error_messages = {}
        with self.assertRaises(ValidationError):
            sch._validate_scheduling_an_occupied_room()
            if sch.error_messages:
                raise ValidationError(sch.error_messages)

    def test_metodo_str_retorna_cliente_e_reserva(self):
        """método __str__ retorna representação do cliente e da reserva"""
        sch = Scheduling(client=self.user, reservation=self.reservation)
        result = sch.__str__()
        expected = f'{self.user} {self.reservation}'
        self.assertEqual(result, expected)

    def test_schedule_criado_com_cliente_e_reserva_correta(self):
        """testa se o agendamento é criado com sucesso se o cliente e a reserva
        for valida
        """
        r = Reservation.objects.filter(room=self.reservation.room).exclude(pk=self.reservation.pk).first()
        r.status = 'A'
        r.active = True
        r.save()

        self.reservation.checkin = datetime.now().date()
        self.reservation.checkout = self.reservation.checkin + timedelta(days=1)
        self.reservation.save()

        sch = Scheduling(client=self.user, reservation=self.reservation)
        sch.full_clean()
        sch.save()

        result = Scheduling.objects.last()
        self.assertEqual(result, sch)

    def test_schedule_levanta_validation_error_com_reserva_invalida(self):
        """testa se o agendamento levanta ValidationError com reserva invalida"""
        self.reservation.checkin = datetime.now().date()
        self.reservation.checkout = self.reservation.checkin + timedelta(days=1)
        self.reservation.save()

        sch = Scheduling(client=self.user, reservation=self.reservation)
        with self.assertRaises(ValidationError):
            sch.full_clean()
