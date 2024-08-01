from django.utils.timezone import now
from django.db import models
from django.core.validators import validate_email, RegexValidator, MaxLengthValidator, MinLengthValidator
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from .validators import validate_phone_number
from utils.supportmodels import ClientRules, ClientErrorMessages, ContactErrorMessages
from django.contrib.auth.models import AbstractUser
from .validators import CpfValidator


class Client(AbstractUser):
    """model que representa o usuário final"""
    username = models.CharField(
        max_length=ClientRules.USERNAME_MAX_SIZE,
        unique=True,
        validators=[
            MinLengthValidator(ClientRules.USERNAME_MIN_SIZE, ClientErrorMessages.INVALID_USERNAME_LEN),
            MaxLengthValidator(ClientRules.USERNAME_MAX_SIZE, ClientErrorMessages.INVALID_USERNAME_LEN),
            UnicodeUsernameValidator(),
        ],
        error_messages={
            'blank': ClientErrorMessages.NOT_PROVIDED_USERNAME,
            'null': ClientErrorMessages.NOT_PROVIDED_USERNAME,
            'unique': ClientErrorMessages.DUPLICATED_USERNAME,
            'invalid': ClientErrorMessages.INVALID_USERNAME_CHARS,
        },
    )
    first_name = models.CharField(
        'Nome',
        max_length=ClientRules.MAX_FIRSTNAME_CHARS, 
        blank=False, 
        null=False,
        validators=[
            RegexValidator(r'^[A-Za-z]+$', ClientErrorMessages.INVALID_FIRSTNAME_LETTERS),
            MaxLengthValidator(ClientRules.MAX_FIRSTNAME_CHARS, ClientErrorMessages.INVALID_FIRSTNAME_MAX_LENGTH),
            MinLengthValidator(ClientRules.MIN_FIRSTNAME_CHARS, ClientErrorMessages.INVALID_FIRSTNAME_MIN_LENGTH)
        ],
    )
    last_name = models.CharField(
        'Sobrenome',
        max_length=ClientRules.MAX_SURNAME_CHARS, 
        blank=False, 
        null=False,
        validators=[
            RegexValidator(r'^[A-Za-z][A-Za-z ]*$',  ClientErrorMessages.INVALID_SURNAME_LETTERS),
            MinLengthValidator(ClientRules.MIN_SURNAME_CHARS, ClientErrorMessages.INVALID_SURNAME_MIN_LENGTH),
            MaxLengthValidator(ClientRules.MAX_SURNAME_CHARS, ClientErrorMessages.INVALID_SURNAME_MAX_LENGTH),
        ],
    )
    birthdate = models.DateField(
        'Data de nascimento',
        blank=False, 
        null=False
    )
    email = models.EmailField(
        'E-mail', 
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
        }
    )
    phone = models.CharField(
        'Telefone',
        max_length=11, 
        null=False, 
        blank=False,
        unique=True,
        validators=[
            validate_phone_number,
        ],
        error_messages={
            'blank': ClientErrorMessages.NOT_PROVIDED_PHONE,
            'null': ClientErrorMessages.NOT_PROVIDED_PHONE,
            'unique': ContactErrorMessages.DUPLICATED_PHONE,
            'invalid': ContactErrorMessages.INVALID_PHONE
        }
    )
    cpf = models.CharField(
        'CPF',
        max_length=11,
        unique=True,
        blank=False,
        null=False,
        validators=[
            CpfValidator(message=ClientErrorMessages.INVALID_CPF),
        ],
        error_messages={
            'unique': ClientErrorMessages.DUPLICATED_CPF
        }
    )

    def clean(self) -> None:
        super().clean()
        self.error_messages = {}
        self._validate_username()
        self._validate_password_strength()
        self._validate_birthdate()
        
        if self.error_messages: raise ValidationError(self.error_messages)
    
    def _validate_username(self):
        """faz todas as validações relacionadas ao username"""
        if len(self.username) < ClientRules.USERNAME_MIN_SIZE:
            self.error_messages['username'] = ClientErrorMessages.INVALID_USERNAME_LEN
        
        elif self.username.isnumeric():
            self.error_messages['username'] = ClientErrorMessages.INVALID_USERNAME_CHARS

    def _validate_birthdate(self):
        """faz todas as validações relacionadas a data de nascimento do usuário"""
        if not ClientRules.MIN_AGE <= self.age <= ClientRules.MAX_AGE:
            self.error_messages['birthdate'] = ClientErrorMessages.INVALID_BIRTHDATE
    
    def _validate_password_strength(self):
        """valida o tamanho da senha e se não há símbolos"""
        so_small = len(self.password) < ClientRules.PASSWORD_MIN_SIZE
        no_symbols = self.password.isnumeric() or self.password.isalnum()

        if so_small or no_symbols:
            self.error_messages['password'] =  ClientErrorMessages.PASSWORD_WEAK

    def __str__(self) -> str:
        return self.username

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
        mask = [maskchar if start <= i <= end else d for i, d in enumerate(value)]
        mask = ''.join(mask)
        return mask

    @property
    def complete_name(self) -> str:
        """retorna o nome completo do usuário com as primeiras letras maiúsculas"""
        return self.get_full_name().title()
    
    @property
    def age(self) -> int:
        """retorna a idade do usuário"""
        return now().year - self.birthdate.year
            
    @property
    def formatted_phone(self) -> str:
        """retorna o telefone do usuário no formato (xx) xxxx-xxxx"""
        phone = self.phone
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
    def masked_cpf(self):
        """cpf com dígitos mascarados"""
        masked = self._create_mask(self.cpf, *ClientRules.CPF_MASK_RANGE)
        return masked

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
