from datetime import date
from typing import Annotated

from pydantic import AfterValidator, EmailStr, PastDate, StringConstraints

import exceptions
from clients.error_messages import ClientErrorMessages
from clients.rules import ClientRules

Username = Annotated[
    str,
    StringConstraints(
        pattern=r'^[a-zA-Z0-9_]+$',
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
        raise exceptions.Error(ClientErrorMessages.INVALID_BIRTHDATE)

    return value


Birthdate = Annotated[
    PastDate, AfterValidator(__birthdate_validate), 'Represents a birthdate value object.'
]

Email = Annotated[EmailStr, 'Represents an email value object.']

PhoneNumber = Annotated[
    str,
    StringConstraints(
        pattern=r'^\(\d{2}\)\s\d{4,5}-\d{4}$',
        min_length=ClientRules.PHONE_NUMBER_MIN_SIZE,
        max_length=ClientRules.PHONE_NUMBER_MAX_SIZE,
        strip_whitespace=True,
    ),
    'Represents a phone number value object.',
]

CPF = Annotated[
    str,
    StringConstraints(
        pattern=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
        min_length=ClientRules.CPF_MIN_SIZE,
        max_length=ClientRules.CPF_MAX_SIZE,
        strip_whitespace=True,
    ),
    'Represents a CPF value object.',
]

Password = Annotated[
    str,
    StringConstraints(
        min_length=ClientRules.PASSWORD_MIN_SIZE,
        max_length=ClientRules.PASSWORD_MAX_SIZE,
        strip_whitespace=True,
    ),
    'Represents a password value object.',
]
