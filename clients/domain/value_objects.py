from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import AfterValidator, EmailStr, PastDate, StringConstraints

import exc
from clients.rules import ClientRules
from utils.string_utils import sanitize_digits

from ..feedback_messages import ClientErrorMessages

Username = Annotated[
    str,
    StringConstraints(
        pattern=r'^[a-zA-Z0-9_@.{2,150}\-]+$',
        min_length=ClientRules.USERNAME_MIN_SIZE,
        max_length=ClientRules.USERNAME_MAX_SIZE,
        strip_whitespace=True,
    ),
    'Represents a username value object.',
]


def __birthdate_validate(value: date) -> date:
    today = date.today()
    month_less = today.month < value.month
    day_less = today.month == value.month and today.day < value.day

    age = today.year - value.year - (month_less or day_less)
    if not (ClientRules.MIN_AGE <= age <= ClientRules.MAX_AGE):
        raise exc.Error(ClientErrorMessages.INVALID_BIRTHDATE)

    return value


Birthdate = Annotated[
    PastDate, AfterValidator(__birthdate_validate), 'Represents a birthdate value object.'
]

Email = Annotated[EmailStr, 'Represents an email value object.']

PhoneNumber = Annotated[
    str,
    StringConstraints(
        # pattern=r'^\(\d{2}\)\s\d{4,5}-\d{4}$',
        min_length=ClientRules.PHONE_NUMBER_MIN_SIZE,
        max_length=ClientRules.PHONE_NUMBER_MAX_SIZE,
        strip_whitespace=True,
    ),
    'Represents a phone number value object.',
]


def __cpf_validate(value: str) -> str:
    sanitized = sanitize_digits(value)
    if len(sanitized) != ClientRules.CPF_MAX_LEN:
        raise exc.Error(ClientErrorMessages.INVALID_CPF)
    return sanitized


CPF = Annotated[
    str,
    StringConstraints(
        pattern=r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$',
        min_length=ClientRules.CPF_MIN_SIZE,
        max_length=ClientRules.CPF_MAX_SIZE,
        strip_whitespace=True,
    ),
    AfterValidator(__cpf_validate),
    'Represents a CPF value object.',
]


Password = Annotated[
    str,
    StringConstraints(
        min_length=ClientRules.PASSWORD_MIN_SIZE,
        strip_whitespace=True,
    ),
    'Represents a password value object.',
]


FirstName = Annotated[
    str,
    StringConstraints(
        pattern=ClientRules.FIRST_NAME_PATTERN,
        min_length=ClientRules.MIN_FIRSTNAME_CHARS,
        max_length=ClientRules.MAX_FIRSTNAME_CHARS,
        strip_whitespace=True,
    ),
    'Represents a first name value object.',
]

LastName = Annotated[
    str,
    StringConstraints(
        min_length=ClientRules.MIN_SURNAME_CHARS,
        max_length=ClientRules.MAX_SURNAME_CHARS,
        pattern=ClientRules.LAST_NAME_PATTERN,
        strip_whitespace=True,
    ),
    'Represents a last name value object.',
]


class Language(str, Enum):
    """Enumerates the supported languages."""

    EN = 'en'
    PT_BR = 'pt-br'
