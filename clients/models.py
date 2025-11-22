from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
    validate_email,
)
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from clients.infra.validators import PasswordValidator

from .feedback_messages import ClientErrorMessages, ContactErrorMessages
from .infra.validators import (
    BirthDateValidator,
    PhoneNumberValidator,
    UsernameValidator,
)
from .rules import ClientRules
from .validators import CpfValidator


class Client(AbstractUser):
    """model que representa o usuário final"""

    _PW_VALIDATORS = [
        PasswordValidator([validate_password], raise_exc=True).validate,
    ]

    username = models.CharField(
        _('username'),
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
    )
    first_name = models.CharField(
        _('Nome'),
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
    )
    last_name = models.CharField(
        _('Sobrenome'),
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
    )
    birthdate = models.DateField(
        _('Data de nascimento'),
        blank=False,
        null=False,
        validators=[
            BirthDateValidator(raise_exc=True).validate,
        ],
    )
    email = models.EmailField(
        _('E-mail'),
        max_length=255,
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
    )
    phone = models.CharField(
        _('Telefone'),
        max_length=16,
        null=False,
        blank=False,
        unique=True,
        validators=[
            PhoneNumberValidator(raise_exc=True).validate,
        ],
        error_messages={
            'blank': ClientErrorMessages.NOT_PROVIDED_PHONE,
            'null': ClientErrorMessages.NOT_PROVIDED_PHONE,
            'unique': ContactErrorMessages.DUPLICATED_PHONE,
            'invalid': ContactErrorMessages.INVALID_PHONE,
        },
    )
    cpf = models.CharField(
        _('CPF'),
        max_length=11,
        unique=True,
        blank=False,
        null=False,
        validators=[
            CpfValidator(message=ClientErrorMessages.INVALID_CPF),
        ],
        error_messages={'unique': ClientErrorMessages.DUPLICATED_CPF},
        help_text=_('Seu CPF sem pontuação'),
    )

    def __str__(self) -> str:
        return str(self.username)

    def clean(self):
        super().clean()
        for pw_validator in self._PW_VALIDATORS:
            result = pw_validator(self.password)
            if result.is_err():
                raise ValidationError(result.unwrap_err().msg)

    @staticmethod
    def _create_mask(value: str, start: int, end: int, maskchar='*') -> str:
        """substitui caracteres pelo caractere especificado por `mask_char`
        indo de start até end incluindo end

        Args:
            value (str): valor a ser mascarado
            start (int): index de inicio da mascara
            end (int): index negativo de onde a mascara termina.
            maskchar (str, optional): o caractere usado para fazer a mascara. Defaults to '*'.

        Raises:
            ValueError: caso `end` não seja negativo

        Returns:
            str: valor mascarado
        """
        if end > 0:
            raise ValueError('end must be a negative value')

        end = len(value) + end
        mask_list = [maskchar if start <= i <= end else d for i, d in enumerate(value)]
        masked_value = ''.join(mask_list)
        return masked_value

    @property
    def complete_name(self) -> str:
        """retorna o nome completo do usuário com as primeiras letras maiúsculas"""
        return str(self.get_full_name().title())

    @property
    def age(self) -> int:
        """retorna a idade do usuário"""
        return int(now().year - self.birthdate.year)

    @property
    def formatted_phone(self) -> str:
        """retorna o telefone do usuário no formato (xx) xxxx-xxxx"""
        phone: str = self.phone
        ddd = phone[:2]
        mid = -4
        phone = f'({ddd}) {phone[2:mid]}-{phone[mid:]}'
        return phone

    @property
    def masked_phone(self) -> str:
        """retorna o telefone com dígitos mascarados"""
        return self._create_mask(self.phone, *ClientRules.PHONE_MASK_RANGE)

    @property
    def masked_email(self) -> str:
        """retorna o email com caracteres mascarados"""
        return self._create_mask(self.email, *ClientRules.EMAIL_MASK_RANGE)

    @property
    def masked_cpf(self) -> str:
        """cpf com dígitos mascarados"""
        masked = self._create_mask(self.cpf, *ClientRules.CPF_MASK_RANGE)
        return masked

    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')
