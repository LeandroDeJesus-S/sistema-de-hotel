from typing import Self

from pydantic import model_validator

from base.entity import BaseEntity
from clients.domain.value_objects import CPF, Email, Password, Username

from ..feedback_messages import ChangePassword, SignIn, SignUp

_signin_msg = {
    'missing': SignIn.INVALID_CREDENTIALS,
    'string_pattern_mismatch': SignIn.INVALID_CREDENTIALS,
    'string_too_long': SignIn.INVALID_CREDENTIALS,
    'string_too_short': SignIn.INVALID_CREDENTIALS,
    'value_error': SignIn.INVALID_CREDENTIALS,
}

_signup_msg = {
    'missing': SignUp.MISSING_FIELDS,
    'string_pattern_mismatch': SignUp.INVALID_USERNAME,
    'string_too_long': SignUp.INVALID_USERNAME,
    'string_too_short': SignUp.INVALID_USERNAME,
    'value_error': SignUp.INVALID_USERNAME,
}


class SignUpInput(BaseEntity):
    """
    A Pydantic model to validate the sign-up data.
    This is our data contract.
    """

    _messages = {
        'username': _signup_msg,
        'password': _signup_msg,
        'first_name': _signup_msg,
        'last_name': _signup_msg,
        'phone': _signup_msg,
        'email': _signup_msg,
        'birthdate': _signup_msg,
        'cpf': _signup_msg,
    }

    username: str  # Use basic str to let domain entity handle Username validation
    password: str  # Use basic str to let domain entity handle Password validation
    first_name: str
    last_name: str
    phone: str
    email: str  # Use basic str to let domain entity handle Email validation
    birthdate: str
    cpf: CPF


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
