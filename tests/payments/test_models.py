from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from reservations.models import Reservation, Room
from clients.models import Client
from payments.models import Payment
from django.core.exceptions import ValidationError
from utils.supportmodels import PaymentErrorMessages


class TestPayment(TestCase):
    def setUp(self) -> None:
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')

        self.user = Client.objects.get(pk=1)
        self.room = Room.objects.get(pk=1)

        checkin = datetime.now().date()
        checkout = (checkin + timedelta(days=5))
        amount = (checkout - checkin).days * self.room.daily_price_in_cents / 100

        self.reservation = Reservation(**{
            'client': self.user,
            'checkin': checkin,
            'checkout': checkout,
            'amount': Decimal(str(amount)),
            'observations': '*' * 100,
            'room': self.room,
        })
        self.reservation.save()
        self.payment = Payment(reservation=self.reservation, amount=self.reservation.amount)
        self.payment.save()

        self.saved_payment = Payment.objects.get(pk=self.payment.pk)

    def test_data_e_atribuida_a_pagamento(self):
        """testa se a data de criação do pagamento é atribuida corretamente ao pagamento"""
        self.assertAlmostEqual(self.saved_payment.date.timestamp(), datetime.now().timestamp(), delta=0.01)

    def test_cliente_atribuido_a_pagamento(self):
        """testa se o cliente é atribuido corretamente ao pagamento"""
        self.assertEqual(self.saved_payment.reservation.client, self.user)

    def test_room_atribuido_a_pagamento(self):
        """testa se o quarto é atribuido corretamente ao pagamento"""
        self.assertEqual(self.saved_payment.reservation.room, self.room)

    def test_amount_atribuido_a_pagamento(self):
        """testa se o valor total a ser pago é atribuido corretamente ao pagamento"""
        self.assertEqual(self.saved_payment.reservation.amount, self.reservation.amount)

    def test_reserva_atribuida_a_pagamento(self):
        """testa se a reserva é atribuida corretamente ao pagamento"""
        self.assertEqual(self.saved_payment.reservation, self.reservation)

    def test_status_inicial_e_processando(self):
        """testa se o status ao iniciar o pagamento é P de processando"""
        self.assertEqual(self.saved_payment.status, 'P')

    def test_validationerror_se_valor_do_pagamento_diferente_do_amount_da_reserva(self):
        """testa se levanta ValidationError caso o valor do pagamento seja diferente do 
        valor total da reserva
        """
        payment = Payment(reservation=self.reservation, amount=Decimal('10000'))
        with self.assertRaisesMessage(ValidationError, PaymentErrorMessages.INVALID_PAYMENT_VALUE):
            payment.full_clean()

    def test_pagamento_savo_com_dados_validos(self):
        """testa se o pagamento é persistido com todos os dados validos"""
        reserva = Reservation(**{
            'client': Client.objects.first(),
            'checkin': datetime.now().date(),
            'checkout': datetime.now().date() + timedelta(days=1),
            'amount': Decimal(str(self.room.daily_price)),
            'observations': '*'*100,
            'room': self.room,
        })
        reserva.full_clean()
        reserva.save()

        payment = Payment(reservation=reserva, amount=reserva.amount)
        payment.full_clean()
        payment.save()

        result = Payment.objects.last()
        self.assertEqual(result, payment)

    def test_metodo_str_retorna_nome_da_classe_com_respectivo_id(self):
        """testa se o método __str__ irá retornar o nome da Model com respectivo id
        do objeto"""
        result = self.payment.__str__()
        expected = f'{Payment.__name__} {self.payment.pk}'
        self.assertEqual(result, expected)
