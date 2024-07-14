from django.utils.timezone import now
from django.db import models
from django.core.validators import validate_email, RegexValidator
from django.core.exceptions import ValidationError
from .validators import validate_phone_number, ValidateFieldLength
from django.conf import settings


class Cliente(models.Model):
    nome = models.CharField(
        'Nome', 
        max_length=25, 
        blank=False, 
        null=False,
        validators=[
            ValidateFieldLength('Primeiro nome', 2, 25), 
            RegexValidator(r'[A-Za-z]{2,25}', 'O nome deve conter apenas letras')
        ],
    )
    sobrenome = models.CharField(
        'Sobrenome', 
        max_length=50, 
        blank=False, 
        null=False,
        validators=[
            ValidateFieldLength('Sobrenome', 2, 50), 
            RegexValidator(r'[A-Za-z]{2,50}',  'O nome deve conter apenas letras')
        ],
    )
    nascimento = models.DateField(
        'Data de nascimento', 
        blank=True, 
        null=True
    )

    def __str__(self) -> str:
        return self.complete_name

    @property
    def complete_name(self):
        return f'{self.nome} {self.sobrenome}'.capitalize()
    
    @property
    def age(self):
        if self.nascimento:
            return now().year - self.nascimento.year

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['nome', 'sobrenome', 'nascimento'],
                name='unique_client',
            )
        ]

    def clean(self) -> None:
        super().clean()
        error_messages = {}
        if not settings.CLIENT_MIN_AGE < self.age < settings.CLIENT_MAX_AGE:
            error_messages['nascimento'] = 'Data de nascimento inválida.'
        
        if error_messages: raise ValidationError({})

    def solicite_reservation(self, reservation, room):
        if room.disponivel:
            reservation.quarto = room
        

class Contato(models.Model):
    email = models.EmailField(
        'E-mail', 
        max_length=255, 
        unique=True, 
        null=False, 
        blank=False, 
        validators=[
            validate_email,
        ]
    )
    telefone = models.CharField(
        'Telefone', 
        max_length=11, 
        null=False, 
        blank=False, 
        validators=[
            validate_phone_number,
        ]
    )
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='contatos', 
        related_query_name='contato'
    )

    def __str__(self) -> str:
        return f'{self.cliente.nome} telefone: {self.telefone} e-mail: {self.email}'
    
    @staticmethod
    def _create_mask(value, start, end, maskchar='*'):
        mask = [maskchar if start <= i <= end else d for i, d in enumerate(value)]
        mask = ''.join(mask)
        return mask
    
    @property
    def formatted_phone(self):
        phone = self.telefone
        ddd = phone[:2]
        mid = len(phone[2:]) // 2
        phone = f'({ddd}) {phone[2:mid]}-{phone[mid:]}'
        return phone

    @property
    def masked_phone(self):
        return self._create_mask(self.telefone, start=3, end=len(self.telefone) - 5)
    
    @property
    def masked_email(self):
        email = self.email.split('@')[0]
        end = len(email) - 1
        self._create_mask(self.email, start=3, end=end)
