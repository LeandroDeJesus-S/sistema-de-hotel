from django.test import TestCase
from django.core.management import call_command
from home.models import Hotel, Contact


class TestHotel(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        self.hotel = Hotel.objects.get(pk=1)

    def test_str_retorna_nome_do_hotel(self):
        self.assertEqual(self.hotel.__str__(), self.hotel.name)


class TestContact(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/contato_fixture.json')

        self.contact = Contact.objects.get(pk=1)

    def test_str_retorna_nome_da_model_e_id(self):
        self.assertEqual(self.contact.__str__(), 'Contact 1')
