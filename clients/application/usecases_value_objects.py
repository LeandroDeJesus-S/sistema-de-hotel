from base.entity import BaseEntity
from clients.domain.value_objects import Email, Password, Username
from clients.error_messages import SignInMessages

_signin_msg = {
    'missing': SignInMessages.INVALID_CREDENTIALS,
    'string_pattern_mismatch': SignInMessages.INVALID_CREDENTIALS,
    'string_too_long': SignInMessages.INVALID_CREDENTIALS,
    'string_too_short': SignInMessages.INVALID_CREDENTIALS,
    'value_error': SignInMessages.INVALID_CREDENTIALS,
}


class SignInSchema(BaseEntity):
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
