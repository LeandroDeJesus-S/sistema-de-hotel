from datetime import datetime, timedelta
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from reservations.models import Reservation
from payments.models import Payment
from reservations.tasks import check_reservation_dates, release_room

class TestTasks(TestCase):
    def setUp(self) -> None:
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')
    
    def test_check_reservation_dates(self):
        """testa se a função check_reservation_dates desativa, finaliza a reserva e libera
        o quarto corretamente
        """
        for r in Reservation.objects.all():
            r.checkout = datetime.now().date() - timedelta(days=1)
            r.active = True
            r.room.available = False
            r.room.save()
            r.save()
        
        check_reservation_dates()

        for r in Reservation.objects.all():
            with self.subTest(reservation=r):
                self.assertListEqual(
                    [r.active, r.status, r.room.available],
                    [False, 'F', True],
                )
        
    def test_release_room_libera_quarto_corretamente(self):
        """testa se a task release_room libera o quarto corretamente
        caso ele não tenha um pagamento finalizado
        """
        for r in Reservation.objects.all():
            r.room.available = False
            r.room.save()
            r.save()
        
            release_room(r.pk)
            with self.subTest(reservation=r):
                r = Reservation.objects.get(pk=r.pk)
                self.assertTrue(r.room.available)
    
    def test_release_room_nao_libera_quarto_caso_reserva_tenha_pagamento_finalizado(self):
        """testa se a task release_room não libera o quarto caso tenha um pagamento finalizado
        """
        for r in Reservation.objects.all():
            r.room.available = False
            r.room.save()
            r.save()
        
            Payment.objects.create(reservation=r, amount=r.amount, status='F')
            release_room(r.pk)
            
            with self.subTest(reservation=r):
                r = Reservation.objects.get(pk=r.pk)
                self.assertFalse(r.room.available)
    
    @patch('reservations.tasks.Reservation.objects.get')
    def test_release_room_nao_faz_nada_caso_reserva_nao_exista(self, mock_reservation_get):
        """testa se ao passar o id de uma reserva que não existe
        a task não faz nada
        """
        mock_reservation_get.side_effect = Reservation.DoesNotExist
        try:
            release_room(18)
        except Reservation.DoesNotExist:
            self.fail(f'Reservation.DoesNotExist raised')
