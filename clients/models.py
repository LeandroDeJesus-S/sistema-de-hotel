from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
    validate_email,
)
from django.db import models
from django.utils.translation import gettext_lazy as gtl

from clients.infra.validators import (
    BirthDateValidator,
    CpfValidator,
    PasswordValidator,
    PhoneNumberValidator,
    UsernameValidator,
)

from .feedback_messages import ClientErrorMessages, ContactErrorMessages
from .rules import ClientRules


class Client(AbstractUser):
    """model que representa o usuário final"""

    _PW_VALIDATORS = [
        PasswordValidator([validate_password], raise_exc=True).validate,
    ]

    username = models.CharField(
        gtl('username'),
        max_length=ClientRules.USERNAME_MAX_SIZE,
        unique=True,
        validators=[
            MinLengthValidator(
                ClientRules.USERNAME_MIN_SIZE,
                ClientErrorMessages.INVALID_USERNAME_LEN
                % {
                    'min_len': ClientRules.USERNAME_MIN_SIZE,
                    'max_len': ClientRules.USERNAME_MAX_SIZE,
                },
            ),
            MaxLengthValidator(
                ClientRules.USERNAME_MAX_SIZE,
                ClientErrorMessages.INVALID_USERNAME_LEN
                % {
                    'min_len': ClientRules.USERNAME_MIN_SIZE,
                    'max_len': ClientRules.USERNAME_MAX_SIZE,
                },
            ),
            UsernameValidator(dj_extra=[UnicodeUsernameValidator()], raise_exc=True).validate,
        ],
        error_messages={
            'blank': ClientErrorMessages.NOT_PROVIDED_USERNAME,
            'null': ClientErrorMessages.NOT_PROVIDED_USERNAME,
            'unique': ClientErrorMessages.DUPLICATED_USERNAME,
            'invalid': ClientErrorMessages.INVALID_USERNAME_CHARS,
        },
        help_text=gtl(
            'Nome de usuário único para login, deve ter entre %(min)s e %(max)s caracteres'
        )
        % {'min': ClientRules.USERNAME_MIN_SIZE, 'max': ClientRules.USERNAME_MAX_SIZE},
    )
    first_name = models.CharField(
        gtl('Nome'),
        max_length=ClientRules.MAX_FIRSTNAME_CHARS,
        blank=False,
        null=False,
        validators=[
            RegexValidator(
                ClientRules.FIRST_NAME_PATTERN,
                ClientErrorMessages.INVALID_FIRSTNAME_LETTERS,
            ),
            MaxLengthValidator(
                ClientRules.MAX_FIRSTNAME_CHARS,
                ClientErrorMessages.INVALID_FIRSTNAME_MAX_LENGTH,
            ),
            MinLengthValidator(
                ClientRules.MIN_FIRSTNAME_CHARS,
                ClientErrorMessages.INVALID_FIRSTNAME_MIN_LENGTH,
            ),
        ],
        help_text=gtl(
            'Nome próprio do cliente, apenas letras e espaços (máximo %(max)s caracteres)'
        )
        % {'max': ClientRules.MAX_FIRSTNAME_CHARS},
    )
    last_name = models.CharField(
        gtl('Sobrenome'),
        max_length=ClientRules.MAX_SURNAME_CHARS,
        blank=False,
        null=False,
        validators=[
            RegexValidator(
                ClientRules.LAST_NAME_PATTERN,
                ClientErrorMessages.INVALID_SURNAME_LETTERS,
            ),
            MinLengthValidator(
                ClientRules.MIN_SURNAME_CHARS,
                ClientErrorMessages.INVALID_SURNAME_MIN_LENGTH,
            ),
            MaxLengthValidator(
                ClientRules.MAX_SURNAME_CHARS,
                ClientErrorMessages.INVALID_SURNAME_MAX_LENGTH,
            ),
        ],
        help_text=gtl(
            'Sobrenome do cliente, apenas letras e espaços (máximo %(max)s caracteres)'
        )
        % {'max': ClientRules.MAX_SURNAME_CHARS},
    )
    birthdate = models.DateField(
        gtl('Data de nascimento'),
        blank=False,
        null=False,
        validators=[
            BirthDateValidator(raise_exc=True).validate,
        ],
        help_text=gtl('Data de nascimento no formato DD/MM/AAAA'),
    )
    email = models.EmailField(
        gtl('E-mail'),
        max_length=ClientRules.EMAIL_MAX_LEN,
        unique=True,
        null=False,
        blank=False,
        validators=[
            validate_email,
        ],
        error_messages={
            'null': ClientErrorMessages.NOT_PROVIDED_EMAIL,
            'blank': ClientErrorMessages.NOT_PROVIDED_EMAIL,
            'unique': ContactErrorMessages.DUPLICATED_EMAIL,
            'invalid': ContactErrorMessages.INVALID_EMAIL,
        },
        help_text=gtl('Endereço de e-mail único do cliente (máximo %(max)s caracteres)')
        % {'max': ClientRules.EMAIL_MAX_LEN},
    )
    phone = models.CharField(
        gtl('Telefone'),
        max_length=ClientRules.PHONE_NUMBER_MAX_SIZE,
        null=False,
        blank=False,
        unique=True,
        validators=[
            PhoneNumberValidator(raise_exc=True, weak=settings.DEBUG).validate,
        ],
        error_messages={
            'blank': ClientErrorMessages.NOT_PROVIDED_PHONE,
            'null': ClientErrorMessages.NOT_PROVIDED_PHONE,
            'unique': ContactErrorMessages.DUPLICATED_PHONE,
            'invalid': ContactErrorMessages.INVALID_PHONE,
        },
        help_text=gtl(
            'Número de telefone no formato (XX) XXXXX-XXXX (máximo %(max)s caracteres)'
        )
        % {'max': ClientRules.PHONE_NUMBER_MAX_SIZE},
    )
    cpf = models.CharField(
        gtl('CPF'),
        max_length=ClientRules.CPF_MAX_LEN,
        unique=True,
        blank=False,
        null=False,
        validators=[
            CpfValidator(message=ClientErrorMessages.INVALID_CPF, raise_exc=True).validate,
        ],
        error_messages={'unique': ClientErrorMessages.DUPLICATED_CPF},
        help_text=gtl('Seu CPF sem pontuação (máximo %(max)s caracteres)')
        % {'max': ClientRules.CPF_MAX_LEN},
    )

    def __str__(self) -> str:
        return str(self.username)

    def clean(self):
        super().clean()
        for pw_validator in self._PW_VALIDATORS:
            pw_validator(self.password)

    class Meta:
        verbose_name = gtl('Cliente')
        verbose_name_plural = gtl('Clientes')
