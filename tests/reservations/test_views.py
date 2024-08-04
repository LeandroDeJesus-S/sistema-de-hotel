from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse
from reservations.models import Room, Benefit, Reservation
from reservations.views import Rooms
from clients.models import Client
from utils.supportmodels import ReserveErrorMessages, ReserveRules
from django_q.models import Schedule
from utils.supporttest import get_message


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


class TestReservar(Base):
    def setUp(self):
        super().setUp()

        self.user = Client.objects.first()
        self.room1 = Room.objects.first()

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
        self.assertTemplateUsed(response, self.template)

    def test_redireciona_para_checkout_com_dados_validos(self):
        """se tiver dados validos a redireciona para checkout após a reserva criada"""
        self.client.force_login(self.user)
        response = self.client.post(
            path=self.url,
            data=self.valid_data,
        )
        reserva = Reservation.objects.last()
        self.assertRedirects(response, reverse('checkout', args=(reserva.pk,)))

    def test_checkin_com_data_invalida_renderiza_novamente_reserva_com_mensagem(self):
        """testa se renderiza novamente a pagina de reserva com mensagem correta"""
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

    def test_cliente_e_relacionado_a_reserva(self):
        """testa se o cliente é relacionado a reserva corretamente"""
        self.client.force_login(self.user)

        self.client.post(self.url, self.valid_data)
        reserva = Reservation.objects.last()
        self.assertEqual(reserva.client, self.user)
    
    def test_quarto_e_relacionado_a_reserva(self):
        """testa se o quarto é relacionado corretamente a reserva"""
        self.client.force_login(self.user)

        self.client.post(self.url, self.valid_data)
        reserva = Reservation.objects.last()
        self.assertEqual(reserva.room, self.room1)
    
    def test_custo_e_relacionado_a_reserva(self):
        """testa se o custo da reserva é adicionada corretamente"""
        self.client.force_login(self.user)

        self.client.post(self.url, self.valid_data)
        reserva = Reservation.objects.last()

        result = reserva.amount
        expected = Decimal(str(reserva.reservation_days)) * self.room1.daily_price
        self.assertEqual(result, expected)
    
    def test_django_q_schedule_e_criado_quando_reserva_e_iniciada(self):
        """testa se a Schedule de liberar quarto é criada corretamente"""
        self.client.force_login(self.user)
        self.client.post(self.url, self.valid_data)
        last_schedule = Schedule.objects.last()
        
        result = last_schedule.func
        expected = 'reservations.tasks.release_room'
        self.assertEqual(result, expected)


class TestHistoricoReservas(Base):
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
        
        result = list(response.context[self.context_obj_name])
        expected = list(Reservation.objects.filter(client=self.user).order_by('-id'))
        self.assertListEqual(result, expected)

    def test_cliente_nao_logado_redirecionado_para_signin(self):
        """testa se o cliente não estiver logado ele é redirecionado para o signin"""
        response = self.client.get(self.url)
        expected_url = reverse('signin') + f'?next={self.url}'
        self.assertRedirects(response, expected_url)
        