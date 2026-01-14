import re
from datetime import date
from typing import Callable, TypeAlias, TypeVar

import phonenumbers
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.timezone import now
from django.utils.translation import gettext as _

from clients.application.validators import AbsValidator
from clients.feedback_messages import ClientErrorMessages, ContactErrorMessages
from clients.rules import ClientRules
from exc import Result

T = TypeVar('T')
ValidatorCall: TypeAlias = Callable[[T], Result[T] | None]


class UsernameValidator(AbsValidator):
    MIN_LEN = ClientRules.USERNAME_MIN_SIZE
    MAX_LEN = ClientRules.USERNAME_MAX_SIZE

    def __init__(
        self,
        dj_extra: list[ValidatorCall],
        max_len: int = MAX_LEN,
        min_len: int = MIN_LEN,
        raise_exc: bool = False,
    ) -> None:
        """
        Args:
            dj_extra (list): list of django validators
        """
        self._dj_extra = dj_extra
        self._max_len = max_len
        self._min_len = min_len
        self.raise_exc = raise_exc

    def validate(self, value: str) -> Result[str]:
        for dj_validator in self._dj_extra:
            dj_validator(value)

        if not (self._min_len <= len(value) <= self._max_len):
            msg = ClientErrorMessages.INVALID_USERNAME_LEN % {
                'min_len': self._min_len,
                'max_len': self._max_len,
            }
            if self.raise_exc:
                raise ValidationError(msg)
            return Result.Err(msg)

        return Result.Ok(value)


class PhoneNumberValidator(AbsValidator):
    """Performs a phone number validation using phonenumbers library"""

    def __init__(self, raise_exc: bool = False, weak: bool = False) -> None:
        self.raise_exc = raise_exc
        self.weak = weak

    def validate(self, value: str) -> Result[str]:  # noqa: PLR6301
        try:
            parsed_phone = phonenumbers.parse(value, 'BR')
            is_possible_number = phonenumbers.is_possible_number(parsed_phone)
            is_valid_number = phonenumbers.is_valid_number(parsed_phone)
            valid = (
                (is_valid_number and is_possible_number)
                if not self.weak
                else is_possible_number
            )

            if not valid:
                if self.raise_exc:
                    raise ValidationError(ContactErrorMessages.INVALID_PHONE)
                return Result.Err(ContactErrorMessages.INVALID_PHONE)
            return Result.Ok(value)

        except phonenumbers.NumberParseException as e:
            if self.raise_exc:
                raise ValidationError(ContactErrorMessages.INVALID_PHONE)
            return Result.Err(ContactErrorMessages.INVALID_PHONE, src_error=e)


class BirthDateValidator(AbsValidator):
    MIN_AGE = ClientRules.MIN_AGE
    MAX_AGE = ClientRules.MAX_AGE

    def __init__(self, min_age=MIN_AGE, max_age=MAX_AGE, raise_exc: bool = False) -> None:
        self._min_age = min_age
        self._max_age = max_age
        self.raise_exc = raise_exc

    def validate(self, value: date) -> Result[date]:
        _now = now()
        age = (_now.year - value.year) - ((_now.month, _now.day) < (value.month, value.day))
        if not (self._min_age <= age <= self._max_age):
            if self.raise_exc:
                raise ValidationError(ClientErrorMessages.INVALID_BIRTHDATE)
            return Result.Err(ClientErrorMessages.INVALID_BIRTHDATE)

        return Result.Ok(value)


class PasswordValidator(AbsValidator):
    MIN_LEN = ClientRules.PASSWORD_MIN_SIZE
    MAX_LEN = ClientRules.PASSWORD_MAX_SIZE
    SYMBOLS = ClientRules.PASSWORD_SUPPORTED_SYMBOLS

    def __init__(
        self,
        dj_extra: list[ValidatorCall],
        max_len: int = MAX_LEN,
        min_len: int = MIN_LEN,
        supported_symbols: str = SYMBOLS,
        raise_exc: bool = False,
    ) -> None:
        self._dj_extra = dj_extra
        self._max_len = max_len
        self._min_len = min_len
        self._supported_symbols = supported_symbols
        self.raise_exc = raise_exc

    def validate(self, value: str) -> Result[str]:
        no_symbols = value.isnumeric() or value.isalnum()
        if not (self._min_len <= len(value) <= self._max_len) or no_symbols:
            msg = ClientErrorMessages.PASSWORD_WEAK % {
                'min_len': self._min_len,
                'max_len': self._max_len,
                'symbols': self._supported_symbols,
            }
            if self.raise_exc:
                raise ValidationError(msg)
            return Result.Err(msg)

        for dj_validator in self._dj_extra:
            dj_validator(value)

        return Result.Ok(value)


class DjangoPasswordValidatorAdapter:
    HELP_MSG = _(
        'A senha deve conter ao menos 8 caracteres, 1 letra maiúscula, '
        '1 letra minúscula, 1 número e 1 caractere especial'
    )

    def __init__(self, validator: AbsValidator | None = None, help_msg: str = HELP_MSG):
        self._validator = validator or PasswordValidator([])
        self._help_msg = help_msg

    def validate(self, password: str, user=None) -> None:
        result = self._validator.validate(password)
        if result.is_err():
            raise ValidationError(result.unwrap_err().msg)

    def get_help_text(self) -> str:
        return self._help_msg


@deconstructible
class CpfValidator(AbsValidator):  # noqa: PLW1641
    _FIRST_DIGIT_THRESHOLD = 9
    _CPF_LENGTH = 11

    def __init__(
        self, message: str = ClientErrorMessages.INVALID_CPF, raise_exc: bool = False
    ) -> None:
        self._cpf = ''
        self._verified_cpf = ''
        self.message = message
        self.raise_exc = raise_exc

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, CpfValidator)
            and self._cpf == value._cpf
            and self._verified_cpf == value._verified_cpf
            and self.message == value.message
        )

    def _calculate_first_digit(self) -> str:
        """Calculates the first digit of the CPF."""
        if not self._cpf:
            return ''  # Should be caught by has_valid_length earlier
        result, m = 0, 10
        for c in self._cpf[:-2]:
            calc = int(c) * m
            result += calc
            m -= 1
        final_result = str(11 - result % 11)
        return final_result if int(final_result) <= self._FIRST_DIGIT_THRESHOLD else '0'

    def _calculate_second_digit(self) -> str:
        """Calculates the second digit of the CPF."""
        if not self._cpf:
            return ''  # Should be caught by has_valid_length earlier
        m, ac = 11, 0
        for i in self._cpf[:-2] + self._calculate_first_digit():
            calc = int(i) * m
            ac += calc
            m -= 1
        final_result = str(11 - ac % 11)
        return final_result if int(final_result) <= self._FIRST_DIGIT_THRESHOLD else '0'

    def _is_valid_sequence(self) -> bool:
        """Checks if the CPF is a sequence (e.g., 000.000.000-00)."""
        if not self._cpf:
            return False
        return self._cpf == self._cpf[0] * len(self._cpf)

    def _has_valid_length(self) -> bool:
        """Checks if the CPF has a valid length."""
        return len(self._cpf) == self._CPF_LENGTH

    def validate(self, value: str) -> Result[str]:
        self._cpf = re.sub(r'\D', '', value)

        if not self._has_valid_length():
            if self.raise_exc:
                raise ValidationError(self.message)
            return Result.Err(self.message)

        if self._is_valid_sequence():
            if self.raise_exc:
                raise ValidationError(self.message)
            return Result.Err(self.message)

        _first_digit = self._calculate_first_digit()
        _second_digit = self._calculate_second_digit()
        self._verified_cpf = self._cpf[:-2]
        self._verified_cpf += _first_digit
        self._verified_cpf += _second_digit  # noqa: E501

        if not self._cpf == self._verified_cpf:
            if self.raise_exc:
                raise ValidationError(self.message)
            return Result.Err(self.message)

        return Result.Ok(value)
