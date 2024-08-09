from django.test import TestCase
from django.core.management import call_command
from reservations.models import Benefit, Room
from restaurants.models import Restaurant


class TestHome(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/restaurante_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')

        self.template = 'static/home/html/home.html'
        self.response = self.client.get('/')
    
    def test_template(self):
        self.assertTemplateUsed(self.response, self.template)
    
    def test_beneficios_enviados_no_context(self):
        """testa se todos os benefícios marcados com displayable_on_homepage=True são enviados no context"""
        result = self.response.context.get('benefits')
        expected = Benefit.objects.filter(displayable_on_homepage=True)
        self.assertQuerysetEqual(result, expected)

    def test_top_4_quartos_mais_procurados_enviados_corretamente(self):
        """envia corretamente os top 4 quartos mais procurados no context"""
        result = self.response.context.get('rooms')
        expected = Room.objects.filter(reservation_room__pk__in=[2, 3, 1, 4])
        self.assertQuerysetEqual(result, expected)

    def test_restaurante_enviado_no_context(self):
        """testa se o restaurante é enviado corretamente no context"""
        result = self.response.context.get('restaurant')
        expected = Restaurant.objects.get(pk=1)
        self.assertEqual(result, expected)
