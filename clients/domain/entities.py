from base.entity import BaseEntity

from ..feedback_messages import ClientErrorMessages, ContactErrorMessages
from .value_objects import (
    CPF,
    Birthdate,
    Email,
    FirstName,
    LastName,
    Password,
    PhoneNumber,
    Username,
)


class Client(BaseEntity):
    """
    Client represents a user client from the hotel.

    Parameters
        username: Username
        first_name: str
        last_name: str
        birthdate: Birthdate
        email: Email
        phone: PhoneNumber
        cpf: CPF
        password: Password
    """

    _messages = {
        'username': {
            'missing': ClientErrorMessages.NOT_PROVIDED_USERNAME,
            'string_too_long': ClientErrorMessages.INVALID_USERNAME_LEN,
            'string_too_short': ClientErrorMessages.INVALID_USERNAME_LEN,
            'string_pattern_mismatch': ClientErrorMessages.INVALID_USERNAME_CHARS,
        },
        'first_name': {
            'string_too_long': ClientErrorMessages.INVALID_FIRSTNAME_MAX_LENGTH,
            'string_too_short': ClientErrorMessages.INVALID_FIRSTNAME_MIN_LENGTH,
            'string_pattern_mismatch': ClientErrorMessages.INVALID_FIRSTNAME_LETTERS,
        },
        'last_name': {
            'string_too_long': ClientErrorMessages.INVALID_SURNAME_MAX_LENGTH,
            'string_too_short': ClientErrorMessages.INVALID_SURNAME_MIN_LENGTH,
            'string_pattern_mismatch': ClientErrorMessages.INVALID_SURNAME_LETTERS,
        },
        'birthdate': {
            'value_error': ClientErrorMessages.INVALID_BIRTHDATE,
            'date_past': ClientErrorMessages.INVALID_BIRTHDATE,
        },
        'email': {
            'missing': ClientErrorMessages.NOT_PROVIDED_EMAIL,
            'value_error': ClientErrorMessages.INVALID_EMAIL,
        },
        'phone': {
            'missing': ClientErrorMessages.NOT_PROVIDED_PHONE,
            'value_error': ContactErrorMessages.INVALID_PHONE,
        },
        'cpf': {
            'value_error': ClientErrorMessages.INVALID_CPF,
        },
        'password': {
            'string_pattern_mismatch': ClientErrorMessages.PASSWORD_WEAK,
        },
    }
    username: Username
    first_name: FirstName
    last_name: LastName
    birthdate: Birthdate
    email: Email
    phone: PhoneNumber
    cpf: CPF
    password: Password
    language: str = 'en'
    id: int | None = None

    def __str__(self) -> str:
        return self.username
