from datetime import datetime, timedelta
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from clients.models import Client
from reservations.models import Room
from schedules.models import Scheduling
from reservations.models import Reservation
from utils.supporttest import get_message
from utils.supportviews import CheckoutMessages, INVALID_RECAPTCHA_MESSAGE
from utils.supportmodels import ReserveErrorMessages
from payments.models import Payment
from django_q.tasks import Schedule


class Base(TestCase):
    def setUp(self) -> None:
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')
        call_command('loaddata', 'tests/fixtures/pagamento_fixture.json')

        self.user = Client.objects.get(pk=1)
        self.room = Room.objects.get(pk=1)
        self.reservation = Reservation.objects.get(pk=1)
        self.payment = Payment.objects.get(pk=1)
        self.schedule = Scheduling.objects.create(client=self.user, reservation=self.reservation)
        self.payment.status = 'P'
        self.payment.save()
    

class CommonTestsMixin:
    def test_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.template)
    
    def test_cliente_nao_logado_redirecionado_para_signin(self):
        """se o cliente não estiver logado ele é redirecionado para a pagina de login"""
        response = self.client.get(self.url)
        url = reverse('signin') + f'?next={self.url}'
        self.assertRedirects(response, url)


class TestSchedules(Base, CommonTestsMixin):
    def setUp(self) -> None:
        super().setUp()
        
        self.other_reservation = Reservation.objects.filter(room=self.room).first()
        self.other_reservation.status = 'A'
        self.other_reservation.active = True
        self.other_reservation.save()

        self.template = 'schedule.html'
        self.url = reverse('schedule', args=[1])

        self.schedule_form_data = {
            'checkin': datetime.now().strftime('%Y-%m-%d'),
            'checkout': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'obs': ''
        }
    
    def test_room_pk_passado_para_o_context(self):
        """testa se o id do quarto é enviado para o context"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        
        result = response.context.get('room_pk')
        expected = 1
        self.assertEqual(result, expected)
    
    @patch('schedules.views.support.verify_captcha')
    @patch('schedules.views.ReservationStripePaymentCreator.session')
    def test_agendamento_criado_se_form_e_valido(self, stripe_session, fake_captcha):
        """agendamento é criado se os dados enviados são validos"""
        fake_captcha.return_value = True
        stripe_session.url = 'http://fakestripesession.com/'

        self.client.force_login(self.user)
        response = self.client.post(self.url, self.schedule_form_data)
        
        sch = Scheduling.objects.last()
        self.assertListEqual(
            [
                sch.reservation.checkin,
                sch.reservation.checkout,
                sch.reservation.observations,
                sch.reservation.client
            ],
            [
                datetime.strptime(self.schedule_form_data['checkin'], '%Y-%m-%d').date(),
                datetime.strptime(self.schedule_form_data['checkout'], '%Y-%m-%d').date(),
                self.schedule_form_data['obs'],
                self.user
            ],
        )

    @patch('schedules.views.support.verify_captcha')
    @patch('schedules.views.Payment.full_clean')
    def test_se_levantar_validation_error_renderiza_novamente_pagina_de_agendamento_com_msg(self, payment_full_clean, fake_captcha):
        """renderiza novamente a pagina de agendamentos com mensagem se ocorrer
        algum erro de validação
        """
        fake_captcha.return_value = True
        payment_full_clean.side_effect = ValidationError({'msg': 'error message'})

        self.client.force_login(self.user)
        response = self.client.post(self.url, self.schedule_form_data)
        
        msg = get_message(response)
        self.assertEqual(msg, 'error message')
        self.assertTemplateUsed(response, self.template)

    @patch('schedules.views.support.verify_captcha')
    @patch('schedules.views.Payment.full_clean')
    def test_se_levantar_operational_error_redireciona_para_quartos_com_msg(self, payment_full_clean, fake_captcha):
        """testa se  caso levantar OperationalError redireciona para os quartos
        com msg correta
        """
        fake_captcha.return_value = True
        payment_full_clean.side_effect = OperationalError

        self.client.force_login(self.user)
        response = self.client.post(self.url, self.schedule_form_data)
        
        msg = get_message(response)
        self.assertEqual(msg, CheckoutMessages.TRANSACTION_BLOCKING)
        self.assertRedirects(response, reverse('rooms'))

    @patch('schedules.views.support.verify_captcha')
    @patch('schedules.views.Payment.full_clean')
    def test_se_levantar_exception_redireciona_para_quartos_com_msg(self, payment_full_clean, fake_captcha):
        """testa se  caso levantar uma exceção inesperada redireciona para os quartos
        com msg correta
        """
        fake_captcha.return_value = True
        payment_full_clean.side_effect = Exception

        self.client.force_login(self.user)
        response = self.client.post(self.url, self.schedule_form_data)
        
        msg = get_message(response)
        self.assertEqual(msg, CheckoutMessages.PAYMENT_FAIL)
        self.assertRedirects(response, reverse('rooms'))

    @patch('schedules.views.support.verify_captcha')
    def test_se_nao_passar_por_validacao_da_reserva_renderiza_novamente_pagina_de_agendamento_com_msg(self, fake_captcha):
        """se nao passar pela validação da reserva e levantar ValidationError renderiza
        novamente a pagina de agendamento com a respectiva msg
        """
        fake_captcha.return_value = True
        self.client.force_login(self.user)
        self.schedule_form_data['checkin'] = str(datetime.now().date() - timedelta(days=1))
        self.schedule_form_data['checkout'] = str(datetime.now().date())

        response = self.client.post(self.url, self.schedule_form_data)
        
        msg = get_message(response)
        self.assertEqual(msg, ReserveErrorMessages.INVALID_CHECKIN_DATE)
        self.assertTemplateUsed(response, self.template)
    
    @patch('schedules.views.support.verify_captcha')
    def test_captcha_invalido_redireciona_para_schedule_com_msg_correta(self, fake_captcha):
        """testa se caso o captcha for invalido redireciona novamente para a pagina de
        agendamentos com a msg correta
        """
        fake_captcha.return_value = False
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.schedule_form_data)
        msg = get_message(response)

        self.assertEqual(msg, INVALID_RECAPTCHA_MESSAGE)
        self.assertRedirects(response, self.url)


class TestScheduleSuccess(Base, CommonTestsMixin):
    def setUp(self) -> None:
        super().setUp()
        self.url = reverse('schedule_success', args=[1])
        self.template = 'schedule_success.html'
        self.schedule_task_name = f'schedule {self.schedule}-{self.user}-{self.reservation}'

    def _response(self):
        """realiza o request e retorna a response"""
        self.client.force_login(self.user)
        return self.client.get(self.url)
    
    def test_pagamento_enviado_no_context(self):
        """testa se o pagamento é enviado no context ao renderizar html"""
        response = self._response()
        result = response.context.get('payment')
        self.assertEqual(result, self.payment)
    
    def test_pagamento_salvo_corretamente(self):
        """testa se o status do pagamento é alterado para finalizado e
        a o status da reserva para agendado corretamente
        """
        self._response()
        self.payment.refresh_from_db()

        self.assertEqual(
            [self.payment.status, self.payment.reservation.status],
            ['F', 'S']
        )
    
    def test_pagamento_com_status_diferente_de_processando_renderiza_novamente_pagina_sem_criar_task(self):
        """se o status do pagamento for diferente de processando ele renderiza a pagina sem 
        criar a schedule task de ativar reserva agendada
        """
        self.payment.status = 'F'
        self.payment.save()
        
        response = self._response()
        self.assertTemplateUsed(response, self.template)
        self.assertFalse(
            Schedule.objects.filter(name=self.schedule_task_name).exists()
        )
    
    def test_cria_schedule_task_corretamente(self):
        """testa se ao finalizar pagamento cria a task de agendamento para
        ativar a reserva na data agendada
        """
        self._response()        
        self.assertTrue(
            Schedule.objects.filter(name=self.schedule_task_name).exists()
        )
