from django.test import TestCase
from payments.templatetags.payment_customtags import money


class TestTags(TestCase):
    def test_tag_money_com_valor_em_string_valido(self):
        """se tag money receber valor numérico valido em string
        retorna formatação valida"""
        result = money('20.255')
        self.assertEqual(result, 'R$20.25')
