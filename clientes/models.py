import re
from datetime import date, datetime
from django.utils.timezone import now
from django.db import models
from django.core.validators import validate_email, RegexValidator, MaxLengthValidator, MinLengthValidator
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from .validators import validate_phone_number, ValidateFieldLength
from utils.supportmodels import ClienteRules, ClienteErrorMessages, ReservaErrorMessages
from django.contrib.auth.models import AbstractUser


class Cliente(AbstractUser):
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
        name='nome',
        max_length=ClienteRules.MAX_FIRSTNAME_CHARS, 
        blank=False, 
        null=False,
        validators=[
            ValidateFieldLength(
                'Nome', 
                ClienteRules.MIN_FIRSTNAME_CHARS, 
                ClienteRules.MAX_FIRSTNAME_CHARS
            ), 
            RegexValidator(r'[A-Za-z]{2,25}', ClienteErrorMessages.INVALID_NAME_LETTERS)
        ],
    )
    last_name = models.CharField(
        'Sobrenome',
        name='sobrenome',
        max_length=ClienteRules.MAX_SURNAME_CHARS, 
        blank=False, 
        null=False,
        validators=[
            ValidateFieldLength(
                'Sobrenome', 
                ClienteRules.MIN_SURNAME_CHARS, 
                ClienteRules.MAX_SURNAME_CHARS
            ), 
            RegexValidator(r'[A-Za-z]{2,50}',  ClienteErrorMessages.INVALID_SURNAME_LETTERS)
        ],
    )
    birthdate = models.DateField(
        'Data de nascimento',
        name='nascimento',
        blank=True, 
        null=True
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
        name='telefone',
        max_length=11, 
        null=False, 
        blank=False, 
        validators=[
            validate_phone_number,
        ]
    )

    def clean(self) -> None:
        super().clean()
        self.error_messages = {}
        self._validate_username()
        self._validate_password_strength()
        self._validate_birthdate()
        
        if self.error_messages: raise ValidationError(self.error_messages)
    
    def _validate_username(self):
        if len(self.username) < ClienteRules.USERNAME_MIN_SIZE:
            self.error_messages['username'] = ClienteErrorMessages.INVALID_USERNAME_LEN
        
        elif self.username.isnumeric():
            self.error_messages['username'] = ClienteErrorMessages.INVALID_USERNAME_CHARS

    def _validate_birthdate(self):
        if not ClienteRules.MIN_AGE <= self.age <= ClienteRules.MAX_AGE:
            self.error_messages['nascimento'] = ClienteErrorMessages.INVALID_BIRTHDATE
    
    def _validate_password_strength(self):
        so_small = len(self.password) < ClienteRules.PASSWORD_MIN_SIZE
        no_symbols = self.password.isnumeric() or self.password.isalnum()

        if so_small or no_symbols:
            self.error_messages['password'] =  ClienteErrorMessages.PASSWORD_WEAK

    def __str__(self) -> str:
        fullname = self.complete_name
        return self.complete_name if fullname else self.username

    @staticmethod
    def _create_mask(value, start, end, maskchar='*'):
        if end > 0:
            raise ValueError('end must be a negative value')

        end = len(value) + end
        mask = [maskchar if start <= i <= end else d for i, d in enumerate(value)]
        mask = ''.join(mask)
        return mask

    @property
    def complete_name(self):
        return f'{self.nome} {self.sobrenome}'
    
    @property
    def age(self):
        if self.nascimento:
            return now().year - self.nascimento.year
            
    @property
    def formatted_phone(self):
        phone = self.telefone
        ddd = phone[:2]
        mid = -4
        phone = f'({ddd}) {phone[2:mid]}-{phone[mid:]}'
        return phone

    @property
    def masked_phone(self):
        return self._create_mask(self.telefone, *ClienteRules.PHONE_MASK_RANGE)
    
    @property
    def masked_email(self):
        return self._create_mask(self.email, *ClienteRules.EMAIL_MASK_RANGE)
