from typing import Self

from pydantic import model_validator

from base.entity import BaseEntity
from clients.domain.value_objects import Email, Password, Username

from ..feedback_messages import ChangePassword, SignIn

_signin_msg = {
    'missing': SignIn.INVALID_CREDENTIALS,
    'string_pattern_mismatch': SignIn.INVALID_CREDENTIALS,
    'string_too_long': SignIn.INVALID_CREDENTIALS,
    'string_too_short': SignIn.INVALID_CREDENTIALS,
    'value_error': SignIn.INVALID_CREDENTIALS,
}


class SignInInput(BaseEntity):
    """
    A Pydantic model to validate the sign-in data.
    This is our data contract.
    """

    _messages = {
        'username': _signin_msg,
        'password': _signin_msg,
    }

    username: Username | Email
    password: Password


class ChangePasswordInput(BaseEntity):
    _messages = {
        'password': {
            'missing': 'Há campos obrigatórios que ainda não foram preenchidos.',
            'value_error': ChangePassword.PASSWORDS_DIFFER,
            'assertion_error': ChangePassword.PASSWORDS_DIFFER,
        },
        'password_repeat': {
            'value_error': ChangePassword.PASSWORDS_DIFFER,
        },
        '__root__': {
            'value_error': ChangePassword.PASSWORDS_DIFFER,
        },
    }
    user_id: int
    password: str
    password_repeat: str

    @model_validator(mode='after')
    def _pw_repeat_validate(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError(ChangePassword.PASSWORDS_DIFFER)
        return self
