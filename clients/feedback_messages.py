from django.utils.translation import gettext_lazy as _

EMAIL_CONFIRMATION_TOKEN_RATE_LIMIT_EXCEEDED = _(
    'Wait a few minutes before requesting a new password change link.'
)


class Generic:
    UNEXPECTED_ERROR = _('An unexpected error occurred. Please try again later.')
    INVALID_DATA = _('Invalid data.')


class Recaptcha:
    INVALID_MESSAGE = _('Invalid captcha, please try again.')


class SignUp:
    MISSING_FIELDS = _('There are still unfilled fields.')
    DUPLICATED_USER = _('User already exists.')
    INVALID_USERNAME = _('Invalid username.')


class SignIn:
    INVALID_CREDENTIALS = _('Invalid credentials, please try again.')
    LOGIN_SUCCESS = _('Hello %(username)s, welcome back.')
    LOCKOUT_MESSAGE = _('Maximum number of attempts exceeded. Please try again later.')


class Profile:
    UPDATE_SUCCESS = _('Profile updated successfully.')


class ChangePassword:
    PASSWORDS_DIFFER = _('Passwords do not match.')
    SUCCESS = _('Password changed successfully.')


class ClientErrorMessages:
    GENERIC = _('Invalid client data.')
    SIGNUP_ERROR = _('Could not create account. Check your details and try again.')

    DUPLICATED_CPF = _('CPF not available.')
    DUPLICATED_USERNAME = _('Username already exists.')

    INVALID_BIRTHDATE = _('Invalid birth date.')
    INVALID_CPF = _('Invalid CPF.')
    INVALID_EMAIL = _('Invalid email.')
    INVALID_FIRSTNAME_MAX_LENGTH = _('First name is too long.')
    INVALID_FIRSTNAME_MIN_LENGTH = _('First name is too short.')
    INVALID_FIRSTNAME_LETTERS = _('First name must contain only letters.')
    INVALID_SURNAME_MAX_LENGTH = _('Surname is too long.')
    INVALID_SURNAME_MIN_LENGTH = _('Surname is too short.')
    INVALID_SURNAME_LETTERS = _('Surname must contain only letters and spaces.')
    INVALID_USERNAME_CHARS = _(
        'Please enter a valid username. The value must contain only letters, '
        'numbers, and the following characters @.+-_'
    )
    INVALID_USERNAME_MIN_LEN = _('Username must be at least %(limit_value)d characters long.')
    INVALID_USERNAME_MAX_LEN = _('Username must be at most %(limit_value)d characters long.')
    INVALID_USERNAME_LEN = _(
        'Username must be between %(min_len)d and %(max_len)d characters long.'
    )

    NOT_PROVIDED_EMAIL = _('Please fill in the email field.')
    NOT_PROVIDED_USERNAME = _('The username cannot be empty.')
    NOT_PROVIDED_PHONE = _('The phone number cannot be empty.')

    PASSWORD_WEAK = _(
        'The password must contain at least %(min_len)d digits, letters,'
        ' numbers and some of the symbols %(symbols)s'
    )


class ContactErrorMessages:
    GENERIC = _('Invalid contact data.')
    DUPLICATED_PHONE = _('Phone number not available.')
    DUPLICATED_EMAIL = _('Email not available.')

    INVALID_PHONE = _('Invalid phone number.')
    INVALID_EMAIL = _('Please enter a valid email address.')
