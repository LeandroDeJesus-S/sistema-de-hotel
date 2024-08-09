from django.test import TestCase
from django.core.exceptions import ValidationError
from clients import validators
from utils.supportmodels import ContactErrorMessages
from string import digits


class TestValidators(TestCase):
    def test_validate_phone_number_com_telefones_invalidos(self):
        """testa se validate_phone_number levanta exception com msg correta 
        com telefone invalido
        """
        invalid_phones = [
            *[d * 15 for d in digits],
            '2189654897',
            '0199654897',
            '(21) 965-4897',
            '(21) 9 965-4897',
            '(21) 9 965 4897',
            '(21)9965-4897',
        ]
        for phone in invalid_phones:
            with self.subTest(phone=phone):
                with self.assertRaisesMessage(ValidationError, ContactErrorMessages.INVALID_PHONE):
                    validators.validate_phone_number(phone)
    
    def test_validate_phone_number_com_telefones_validos(self):
        """testa se validate_phone_number levanta exception com msg correta 
        com telefone invalido
        """
        valid_phones = [
            '2199654897',
            '2198654897',
            '21988654897',
        ]
        for phone in valid_phones:
            with self.subTest(phone=phone):
                try:
                    validators.validate_phone_number(phone)
                except ValidationError:
                    self.fail('ValidationError raised')


    def test_cpf_validator_com_cpf_invalido(self):
        """testa se levanta ValidationError com msg correta se CPF é inválido"""
        invalid_cpfs = [
            *[d*11 for d in digits],
            '12345678910',
            '10987654321',
            '18918918918',
        ]
        for cpf in invalid_cpfs:
            with self.subTest(cpf=cpf):
                with self.assertRaisesMessage(ValidationError, 'teste msg'):
                    v = validators.CpfValidator('teste msg')
                    v(cpf)
    
    def test_cpf_validator_com_cpf_valido(self):
        """testa se não levanta ValidationError com CPF válido"""
        invalid_cpfs = [
            '91483951022',
            '29500917092',
            '61886577099',
        ]
        for cpf in invalid_cpfs:
            with self.subTest(cpf=cpf):
                try:
                    v = validators.CpfValidator('teste msg')
                    v(cpf)
                except ValidationError:
                    self.fail('ValidationError raised')
    
    def test_cpf_validator_eq_magic_method(self):
        """testa se não levanta ValidationError com CPF válido"""

        self.assertEqual(
            validators.CpfValidator(''),
            validators.CpfValidator(''),
        )
 