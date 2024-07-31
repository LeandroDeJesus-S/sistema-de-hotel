from django.utils.timezone import now
from django.db import models
from django.core.validators import validate_email, RegexValidator, MaxLengthValidator, MinLengthValidator
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from .validators import validate_phone_number
from utils.supportmodels import ClienteRules, ClienteErrorMessages
from django.contrib.auth.models import AbstractUser
from .validators import CpfValidator


class Client(AbstractUser):
    """model que representa o usuário final"""
    username = models.CharField(
        max_length=ClienteRules.USERNAME_MAX_SIZE,
        unique=True,
        validators=[
            MinLengthValidator(ClienteRules.USERNAME_MIN_SIZE, ClienteErrorMessages.INVALID_USERNAME_LEN),
            MaxLengthValidator(ClienteRules.USERNAME_MAX_SIZE, ClienteErrorMessages.INVALID_USERNAME_LEN),
            UnicodeUsernameValidator(),
        ],
        error_messages={
            'unique': ClienteErrorMessages.DUPLICATED_USERNAME,
            'invalid': ClienteErrorMessages.INVALID_USERNAME_CHARS
        },
    )
    first_name = models.CharField(
        'Nome',
        max_length=ClienteRules.MAX_FIRSTNAME_CHARS, 
        blank=False, 
        null=False,
        validators=[
            RegexValidator(r'[A-Za-z]{2,25}', ClienteErrorMessages.INVALID_NAME_LETTERS),
            MaxLengthValidator(ClienteRules.MAX_FIRSTNAME_CHARS, ClienteErrorMessages.INVALID_NAME_MAX_LENGTH),
            MinLengthValidator(ClienteRules.MIN_FIRSTNAME_CHARS, ClienteErrorMessages.INVALID_NAME_MIN_LENGTH)
        ],
    )
    last_name = models.CharField(
        'Sobrenome',
        max_length=ClienteRules.MAX_SURNAME_CHARS, 
        blank=False, 
        null=False,
        validators=[
            RegexValidator(r'[A-Za-z]{2,50}',  ClienteErrorMessages.INVALID_SURNAME_LETTERS),
            MinLengthValidator(ClienteRules.MIN_SURNAME_CHARS, ClienteErrorMessages.INVALID_SURNAME_MIN_LENGTH),
            MaxLengthValidator(ClienteRules.MAX_SURNAME_CHARS, ClienteErrorMessages.INVALID_SURNAME_MAX_LENGTH),
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
            'null': ClienteErrorMessages.NOT_PROVIDED_EMAIL,
            'blank': ClienteErrorMessages.NOT_PROVIDED_EMAIL,
        }
    )
    phone = models.CharField(
        'Telefone',
        max_length=11, 
        null=False, 
        blank=False, 
        validators=[
            validate_phone_number,
        ]
    )
    cpf = models.CharField(
        'CPF',
        max_length=11,
        unique=True,
        blank=False,
        null=False,
        validators=[
            CpfValidator(),
        ],
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
        if len(self.username) < ClienteRules.USERNAME_MIN_SIZE:
            self.error_messages['username'] = ClienteErrorMessages.INVALID_USERNAME_LEN
        
        elif self.username.isnumeric():
            self.error_messages['username'] = ClienteErrorMessages.INVALID_USERNAME_CHARS

    def _validate_birthdate(self):
        """faz todas as validações relacionadas a data de nascimento do usuário"""
        if not ClienteRules.MIN_AGE <= self.age <= ClienteRules.MAX_AGE:
            self.error_messages['birthdate'] = ClienteErrorMessages.INVALID_BIRTHDATE
    
    def _validate_password_strength(self):
        """valida o tamanho da senha e se não há símbolos"""
        so_small = len(self.password) < ClienteRules.PASSWORD_MIN_SIZE
        no_symbols = self.password.isnumeric() or self.password.isalnum()

        if so_small or no_symbols:
            self.error_messages['password'] =  ClienteErrorMessages.PASSWORD_WEAK

    def __str__(self) -> str:
        return self.username

    @staticmethod
    def _create_mask(value: str, start: int, end: int, maskchar='*') -> str:
        """substitui caracteres pelo caractere especificado por `mask_char`

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
        return self._create_mask(self.phone, *ClienteRules.PHONE_MASK_RANGE)
    
    @property
    def masked_email(self) -> str:
        """retorna o email com caracteres mascarados"""
        return self._create_mask(self.email, *ClienteRules.EMAIL_MASK_RANGE)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
