import re
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from utils.supportmodels import ContactErrorMessages


def validate_phone_number(phone):
    re_match = re.match(r"^[1-9]\d{0,1}9\d{7,8}$", phone)
    if re_match is None:
        raise ValidationError(ContactErrorMessages.INVALID_PHONE)


@deconstructible
class CpfValidator:
    def __init__(self, message) -> None:
        self._cpf = None
        self._verified_cpf = None
        self._message = message
    
    def __call__(self, cpf):
        self._cpf = cpf
        self._verified_cpf = self.validate()
        if not self.is_valid():
            raise ValidationError(self._message)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, CpfValidator) and 
            value._cpf == self._cpf and 
            self._verified_cpf == value._verified_cpf and
            self._message == value._message
        )
    
    def calculate_first_digit(self) -> str:
        """Calcula o primeiro digito do cpf

        Returns:
            str: resultado do calculo do primeiro digito.
        """
        result, m = 0, 10
        for c in self._cpf[:-2]:
            calc = int(c) * m
            result += calc
            m -= 1

        final_result = str(11 - result % 11)
        return final_result if int(final_result) <= 9 else '0'

    def calculate_second_digit(self) -> str:
        """Calcula o segundo digito do cpf

        Returns:
            str: resultado do calculo do segundo digito.
        """
        m, ac = 11, 0
        for i in self._cpf[:-2] + self.calculate_first_digit():
            calc = int(i) * m
            ac += calc
            m -= 1

        final_result = str(11 - ac % 11)
        return final_result if int(final_result) <= 9 else '0'

    def is_valid(self) -> bool:
        """verifica se o cpf enviado é valido

        Returns:
            bool: True se o cpf é valido ou False se não é valido.
        """
        return True if self._cpf == self._verified_cpf else False
    
    def is_sequence(self) -> bool:
        """Verifica se o cpf enviado é uma sequencia Ex; 000.000.000-00

        Returns:
            bool: True se for uma sequencia de digitos, False se não for
        """
        verify = self._cpf[0] * 11
        return True if verify == self._cpf else False
    
    def has_valid_length(self) -> bool:
        """Verifica se o comprimento do cpf enviado é valido.

        Returns:
            bool: True se o comprimento for valido ou False se não é valido.
        """
        return True if len(self._cpf) == 11 else False

    def validate(self) -> str:
        """Faz verificação de comprimento e sequencia, execulta os calculos do
        primeiro e segundo digito, e forma o cpf para validação.

        Returns:
            str: cpf com calculo do primeiro e segundo digito para validar
        """
        if self.is_sequence() or not self.has_valid_length():
            return False
        base = self._cpf[:-2]
        first_digit = self.calculate_first_digit()
        second_digit = self.calculate_second_digit()
        cpf_to_validation = base + first_digit + second_digit
        return cpf_to_validation
