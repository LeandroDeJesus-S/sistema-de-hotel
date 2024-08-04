import time
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from django.http import HttpResponseForbidden
from reservations.models import Room, Reservation
from clients.models import Client
from payments.models import Payment
from utils.supportviews import PaymentCancelMessages
from utils.supporttest import get_message


class Base(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        self.user = Client.objects.get(pk=1)
        self.user2 = Client.objects.get(pk=2)

        self.room = Room.objects.get(pk=1)
        self.room2 = Room.objects.get(pk=2)
        self.redirect_url_field_name = 'next'

        checkin = datetime.now().date()
        checkout = (checkin + timedelta(days=5))

        custo = (checkout - checkin).days * self.room.daily_price_in_cents / 100
        custo2 = (checkout - checkin).days * self.room2.daily_price_in_cents / 100

        self.reservation = Reservation.objects.create(**{
            'client': self.user,
            'checkin': checkin,
            'checkout': checkout,
            'amount': Decimal(str(custo)),
            'observations': '*'*100,
            'room': self.room,
        })

        self.reservation2 = Reservation.objects.create(**{
            'client': self.user2,
            'checkin': checkin,
            'checkout': checkout,
            'amount': Decimal(str(custo2)),
            'observations': '*'*100,
            'room': self.room2,
        })


class TestCheckout(Base):
    def setUp(self):
        super().setUp()
        self.template = 'checkout.html'
        
        self.url = reverse('checkout', args=(self.reservation.pk,))
        self.url_client2 = reverse('checkout', args=(self.reservation2.pk,))
        

    def test_template(self):
        """testa se renderiza o template correto"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.template)
    
    def test_reserva_e_enviada_no_context(self):
        """testa se a reserva correta é enviada no context"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context['reservation'], self.reservation)

    def test_cliente_nao_logado_e_redirecionado_para_signin(self):
        """se o cliente não estiver logado ele é redirecionado para
        a pagina de login"""
        response = self.client.get(self.url)
        next_url = reverse('signin') + f'?{self.redirect_url_field_name}={self.url}'
        self.assertRedirects(response, next_url)

    def test_usario_tentando_acessar_checkout_de_outro_recebe_http_forbiden(self):
        """testa se o usuário rece erro 403 ao tentar acessar checkout de outro cliente"""
        self.client.force_login(self.user)
        response = self.client.get(self.url_client2)
        self.assertIsInstance(response, HttpResponseForbidden)


class TestPayementSuccess(Base):
    def setUp(self):
        super().setUp()
        self.template = 'success.html'
        self.payment = Payment.objects.create(
            reservation=self.reservation,
            status='P',
            amount=self.reservation.amount
        )
        self.url = reverse('payment_success', args=(self.reservation.pk,))
        self.url2 = reverse('payment_success', args=(self.reservation2.pk,))
        self.next_url_field_name = 'next'
    
    def test_template(self):
        """testa se foi renderizado o template correto"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.template)
    
    def test_payment_recebe_status_como_finalizado(self):
        """testa se o pagamento é atualizado para status finalizado após
        concluido
        """
        self.client.force_login(self.user)
        self.client.get(self.url)
        payment = Payment.objects.get(pk=1)
        self.assertEqual(payment.status, 'F')
    
    def test_reserva_e_ativa(self):
        """testa se o a reserva é ativada corretamente"""
        self.client.force_login(self.user)
        self.client.get(self.url)
        payment = Payment.objects.get(pk=1)
        self.assertListEqual(
            [payment.reservation.status, payment.reservation.active],
            ['A', True]
        )

    def test_cliente_nao_logado_nao_consegue_acessar_paginda_de_sucesso(self):
        """testa se o cliente nao estiver logado ele é redirecionado para
        signin
        """
        response = self.client.get(self.url)
        redirect_url = reverse('signin') + f'?{self.next_url_field_name}={self.url}'
        self.assertRedirects(response, redirect_url)

    def test_se_cliente_tentar_acessar_pagina_de_sucesso_de_outro_recebe_403(self):
        """testa se o cliente tentar acessar pagina de sucesso de outro ele recebe
        http forbiden
        """
        self.client.force_login(self.user)
        response = self.client.get(self.url2)
        self.assertIsInstance(response, HttpResponseForbidden)


class TestPaymentCancel(Base):
    def setUp(self):
        super().setUp()
        self.payment = Payment.objects.create(
            reservation=self.reservation,
            status='P',
            amount=self.reservation.amount
        )
        self.payment2 = Payment.objects.create(
            reservation=self.reservation2,
            status='P',
            amount=self.reservation.amount
        )
        self.template = 'cancel.html'
        self.url = reverse('payment_cancel', args=(self.reservation.pk,))
        self.url2 = reverse('payment_cancel', args=(self.reservation2.pk,))
        self.next_url_field_name = 'next'

    def test_template(self):
        """testa se template correto é renderizado"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.template)

    def test_status_do_pagamento_e_da_reserva_muda_para_cancelado_e_quarto_e_liberado(self):
        """testa se o status da reserva e do pagamento são alterados para cancelado e o quarto
        é liberado novamente
        """
        self.client.force_login(self.user)
        self.client.get(self.url)
        payment = Payment.objects.get(pk=self.payment.pk)
        
        self.assertListEqual(
            [payment.status, payment.reservation.status, payment.reservation.room.available],
            ['C', 'C', True],
        )

    def test_cliente_nao_logado_nao_consegue_acessar_paginda_de_cancelamento(self):
        """testa se o cliente nao estiver logado ele é redirecionado para
        signin
        """
        response = self.client.get(self.url)
        redirect_url = reverse('signin') + f'?{self.next_url_field_name}={self.url}'
        self.assertRedirects(response, redirect_url)

    def test_se_cliente_tentar_acessar_pagina_de_cancelamento_de_outro_recebe_403(self):
        """testa se o cliente tentar acessar pagina de cancelamento de outro ele recebe
        http forbiden
        """
        self.client.force_login(self.user)
        response = self.client.get(self.url2)
        self.assertIsInstance(response, HttpResponseForbidden)
