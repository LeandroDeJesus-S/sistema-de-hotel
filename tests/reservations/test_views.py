from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse
from reservations.models import Room, Benefit, Reservation
from reservations.views import Rooms
from clients.models import Client
from utils.supportmodels import ReserveErrorMessages, ReserveRules
from utils.supportviews import ReserveMessages
from django_q.models import Schedule
from utils.supporttest import get_message
from unittest.mock import patch


class Base(TestCase):
    def setUp(self) -> None:
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')

        self.user = Client.objects.get(pk=1)
        self.room1 = Room.objects.get(pk=1)
        self.room2 = Room.objects.get(pk=2)
        self.room3 = Room.objects.get(pk=3)

        self.url = ''
        self.next_url_field_name = 'next'


class RoomTestMixin:
    def test_beneficios_enviados_no_context(self):
        """testa se todos os benefícios são enviados para o context"""
        response = self.client.get(self.url)
        result = list(response.context[self.benefit_context_name])
        expected = list(Benefit.objects.all())
        self.assertListEqual(result, expected)

    def test_sem_usuario_logado_reservation_on_nao_e_adicionado_ao_context(self):
        """testa se quando não há um usuário logado as reservas ativas de usuario
        não são enviadas ao context pela key reservation_on
        """
        response = self.client.get(self.url)
        result = response.context.get('reservation_on')
        self.assertIsNone(result)
    
    def test_sem_usuario_logado_sem_reservas_ativas_ou_agendadas_nao_adicionam_reservation_on_ao_context(self):
        """testa se quando um usuário logado não possui reservas ativas ou agendadas
        reservation_on não é add ao context
        """
        response = self.client.get(self.url)
        result = response.context.get('reservation_on')
        self.assertIsNone(result)
    
    def test_usuario_logado_sem_reservas_ativas_ou_agendadas_nao_adicionam_reservation_on_ao_context(self):
        """testa se quando um usuário logado não possui reservas ativas ou agendadas
        reservation_on não é add ao context
        """
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        result = response.context.get('reservation_on')
        self.assertIsNone(result)
    
    def test_usuario_logado_com_reservas_ativas_ou_agendadas_adicionam_reservation_on_ao_context(self):
        """testa se quando um usuário logado possui reservas com status de ativa ou agendada
        reservation_on é add ao context
        """
        stts = ['A', 'S']
        for stt in stts:
            with self.subTest(status=stt):
                reservation_on = Reservation.objects.create(
                    checkin=datetime.now().date(),
                    checkout=datetime.now().date() + timedelta(days=1),
                    client=self.user,
                    room=self.room1,
                    status=stt,
                )
                
                self.client.force_login(self.user)
                response = self.client.get(self.url)

                result = response.context.get('reservation_on')
                expected = reservation_on
                self.assertEqual(result, expected)
                reservation_on.delete()


class TestRooms(Base, RoomTestMixin):
    def setUp(self):
        super().setUp()

        self.url = reverse('rooms')
        self.rooms_template = 'rooms.html'
        self.rooms_context_name = 'rooms'
        self.benefit_context_name = 'benefits'

    def test_template(self):
        """testa se rooms esta renderizando o template correto"""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.rooms_template)
    
    def test_todos_os_quartos_sao_passados_para_context_ordenados_por_preco_diario_descendente(self):
        """testa se todos os quartos são passados para o context ordenados
        por daily_price decendente
        """
        self.room2.available = False
        self.room2.save()

        response = self.client.get(self.url)
        result = list(response.context[self.rooms_context_name])
        expected = list(Room.objects.all().order_by('-daily_price'))
        self.assertListEqual(result, expected)


class TestRoom(Base, RoomTestMixin):
    def setUp(self):
        super().setUp()
        self.url = reverse('room', args=(self.room1.pk,))
        self.template = 'room.html'
        self.context_name = 'room'
        self.benefit_context_name = 'benefits'
    
    def test_template(self):
        """testa se esta renderizando o template correto"""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.template)
    
    def test_quarto_enviado_no_context(self):
        """testa se esta enviando o quarto correto no context"""
        response = self.client.get(self.url)
        result = response.context[self.context_name]
        expected = self.room1
        self.assertEqual(result, expected)


class TestReserve(Base):
    def setUp(self):
        super().setUp()
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')

        self.user = Client.objects.first()
        self.room1 = Room.objects.first()

        for r in Reservation.objects.filter(client=self.user):
            r.status = 'I'
            r.save()

        self.url = reverse('reserve', args=(self.room1.pk,))
        self.template = 'reserve.html'

        self.valid_data = {
            'checkin': datetime.now().date(),
            'checkout': datetime.now().date() + timedelta(days=1),
            'obs': '',
        }

    def test_template(self):
        """testa se esta renderizando o template correto"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        print(response)
        self.assertTemplateUsed(response, self.template)

    @patch('reservations.views.support.verify_captcha')
    def test_redireciona_para_checkout_com_dados_validos(self, fake_captcha):
        """se tiver dados validos a redireciona para checkout após a reserva criada"""
        fake_captcha.return_value = True
        self.client.force_login(self.user)
        response = self.client.post(
            path=self.url,
            data=self.valid_data,
        )
        reserva = Reservation.objects.last()
        self.assertRedirects(response, reverse('checkout', args=(reserva.pk,)))

    @patch('reservations.views.support.verify_captcha')
    def test_checkin_com_data_invalida_renderiza_novamente_reserva_com_mensagem(self, fake_captcha):
        """testa se renderiza novamente a pagina de reserva com mensagem correta"""
        fake_captcha.return_value = True
        self.client.force_login(self.user)

        invalid_cases = (
            (
                'checkin_daybefore', 
                (datetime.now() - timedelta(days=1)).date(), 
                ReserveErrorMessages.INVALID_CHECKIN_DATE
            ),
            (
                'checkin_dayexceded', 
                ReserveRules.checkin_anticipation_offset() + timedelta(days=1), 
                ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION
            )
        )

        for case_key, case_value, case_msg in invalid_cases:
            if case_key == 'checkin_dayexceded':
                self.valid_data['checkout'] = case_value + timedelta(days=1)

            with self.subTest(case_key, case_value=case_value):
                self.valid_data['checkin'] = case_value
                response = self.client.post(self.url, self.valid_data)
        
                result = get_message(response)
                expected = case_msg
                self.assertEqual(result, expected)
                self.assertTemplateUsed(response, self.template)


    @patch('reservations.views.support.verify_captcha')
    def test_cliente_e_relacionado_a_reserva(self, fake_captcha):
        """testa se o cliente é relacionado a reserva corretamente"""
        fake_captcha.return_value = True
        self.client.force_login(self.user)

        self.client.post(self.url, self.valid_data)
        reserva = Reservation.objects.last()
        self.assertEqual(reserva.client, self.user)
    
    @patch('reservations.views.support.verify_captcha')
    def test_quarto_e_relacionado_a_reserva(self, fake_captcha):
        """testa se o quarto é relacionado corretamente a reserva"""
        fake_captcha.return_value = True
        self.client.force_login(self.user)

        self.client.post(self.url, self.valid_data)
        reserva = Reservation.objects.last()
        self.assertEqual(reserva.room, self.room1)
    
    @patch('reservations.views.support.verify_captcha')
    def test_custo_e_relacionado_a_reserva(self, fake_captcha):
        """testa se o custo da reserva é adicionada corretamente"""
        fake_captcha.return_value = True
        self.client.force_login(self.user)

        self.client.post(self.url, self.valid_data)
        reserva = Reservation.objects.last()

        result = reserva.amount
        expected = Decimal(str(reserva.reservation_days)) * self.room1.daily_price
        self.assertEqual(result, expected)
    
    @patch('reservations.views.support.verify_captcha')
    def test_django_q_schedule_e_criado_quando_reserva_e_iniciada(self, fake_captcha):
        """testa se a Schedule de liberar quarto é criada corretamente"""
        fake_captcha.return_value = True
        self.client.force_login(self.user)
        self.client.post(self.url, self.valid_data)
        last_schedule = Schedule.objects.last()
        
        result = last_schedule.func
        expected = 'reservations.tasks.release_room'
        self.assertEqual(result, expected)

    def test_cliente_que_ja_tem_reserva_com_status_ativa_ou_agendada_e_redirecionado_para_quartos_com_msg_correta(self):
        """testa se um cliente tentar acessar pagina de realizar reserva
        com uma reserva de status ativa ou agendada ele é redirecionado para a pagina de quartos
        com msg correta
        """
        for status in ['A', 'S']:
            with self.subTest(status=status):
                self.client.force_login(self.user)
                r = Reservation.objects.get(pk=1)
                r.status = status
                r.save()
                
                response = self.client.get(self.url)

                msg = get_message(response)
                result = [msg, response.url]
                expected = [ReserveMessages.ALREADY_HAVE_A_RESERVATION, reverse('rooms')]
                self.assertListEqual(result, expected)

    @patch('reservations.views.support.verify_captcha')
    @patch('reservations.views.convert_date')
    def test_se_erro_inesperado_acontecer_ao_enviar_dados_de_reserva_redireciona_para_quarto_com_msg_correta(self, mock_convert_date, fake_captcha):
        """testa se ao enviar dos dados do formulário ocorrer uma exceção inesperada redireciona para
        pagina do quarto com msg correta
        """
        fake_captcha.return_value = True
        mock_convert_date.side_effect = Exception

        self.client.force_login(self.user)
        response = self.client.post(self.url, self.valid_data)
        msg = get_message(response)

        self.assertListEqual(
            [msg, response.url],
            [ReserveMessages.RESERVATION_FAIL, reverse('room', args=[self.room1.pk])]
        )


class TestReservationsHistory(Base):
    def setUp(self):
        super().setUp()
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')

        self.url = reverse('reservations_history')
        self.context_obj_name = 'reservations'
        self.template = 'reservations_history.html'

    def test_template(self):
        """testa se o template correto esta sendo usado"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.template)

    def test_cliente_logado_tem_acesso_a_suas_reservas(self):
        """testa se quando o cliente estiver logado sera exibido o historico
        de reservas do usuario"""
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        
        result = response.context[self.context_obj_name]
        expected = Reservation.objects.filter(client=self.user, status__in=['A', 'S', 'C', 'F']).order_by('-id')
        self.assertQuerysetEqual(result, expected)

    def test_cliente_nao_logado_redirecionado_para_signin(self):
        """testa se o cliente não estiver logado ele é redirecionado para o signin"""
        response = self.client.get(self.url)
        expected_url = reverse('signin') + f'?{self.next_url_field_name}={self.url}'
        self.assertRedirects(response, expected_url)


class TestReservationHistory(Base):
    def setUp(self) -> None:
        super().setUp()
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')
        self.reservation = Reservation.objects.get(pk=1)
        self.url = reverse('reservation_history', args=[self.reservation.pk])
        self.context_obj_name = 'reservation'
        self.template = 'reservation_history.html'
    
    def test_template(self):
        """testa se renderizou o template correto"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, self.template)    
    
    def test_apenas_quartos_do_cliente_e_passado_para_context(self):
        """testa se é adicionado no context apenas os quartos pertencentes
        ao cliente da sessão atual
        """
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        result = response.context[self.context_obj_name]
        expected = Reservation.objects.get(pk=self.reservation.pk, client=self.user, status__in=['A', 'S', 'C', 'F'])
        self.assertEqual(result, expected)

    def test_cliente_logado_redirecionado_para_signin(self):
        """se cliente não estiver autenticado ele é redirecionado para
        signin
        """
        response = self.client.get(self.url)
        next_url = reverse('signin') + f'?{self.next_url_field_name}={self.url}'
        self.assertRedirects(response, next_url)
