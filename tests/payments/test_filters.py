from django.test import TestCase
from payments.templatetags import payment_customtags as tags


class TestTags(TestCase):
    def test_tag_money_com_valor_em_string_valido(self):
        """se tag money receber valor numérico valido em string
        retorna formatação valida"""
        result = tags.money('20.255')
        self.assertEqual(result, 'R$20.25')

    def test_tag_money_levanta_type_error_se_o_valor_nao_for_str_decimal_ou_float(self):
        """se o valor passado não for uma instancia dos tipos str, Decimal ou float
        levanta TypeError
        """
        self.assertRaises(TypeError, tags.money, [10])

    def test_tag_money_levanta_value_error_se_o_valor_for_uma_str_que_nao_pode_ser_convertida_em_float(self):
        """se o valor passado uma str que não possa ser convertida em float
        levanta ValueError
        """
        self.assertRaises(ValueError, tags.money, '10-5')
