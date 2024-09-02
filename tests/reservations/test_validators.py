from django.test import TestCase
from reservations import validators
from datetime import datetime, date

class TestReservationsValidators(TestCase):
    def test_convert_date_com_data_valida(self):
        str_date = '2024-02-01'
        result = validators.convert_date(str_date)
        expected = date(2024, 2, 1)
        self.assertEqual(result, expected)
    
    def test_convert_date_com_formato_de_data_invalida(self):
        """testa se ao passar um formato de data inválida retorna data 1-1-1"""
        str_date = '01022024'
        result = validators.convert_date(str_date)
        expected = date(1, 1, 1)
        self.assertEqual(result, expected)
