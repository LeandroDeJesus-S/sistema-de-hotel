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


@deconstructible
class DjangoValidatorAdapter:
    """A django validator to handle abs validators"""

    def __init__(self, validator: AbsValidator):
        self._validator = validator

    def __call__(self, value: object) -> None:
        result = self._validator.validate(value)
        if result.is_err():
            raise ValidationError(result.unwrap_err().msg)

    def __hash__(self) -> int:
        return hash(self._validator.__class__.__name__)

    def __eq__(self, value: object) -> bool:
        return self._validator.__class__.__name__ == value.__class__.__name__


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

    def __init__(self, raise_exc: bool = False) -> None:
        self.raise_exc = raise_exc

    def validate(self, value: str) -> Result[str]:  # noqa: PLR6301
        try:
            parsed_phone = phonenumbers.parse(value, 'BR')
            if not phonenumbers.is_valid_number(parsed_phone):
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
