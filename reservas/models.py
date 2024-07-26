from datetime import datetime
from decimal import Decimal
import re

from django.core.validators import (
    FileExtensionValidator, 
    MaxValueValidator,
    MinValueValidator,
    RegexValidator, 
    validate_image_file_extension,
)
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image

from clientes.models import Cliente
from home.models import Hotel
from utils.supportmodels import ReservaRules, ReservaErrorMessages, QuartoRules, ClasseErrorMessages, QuartoErrorMessages


class Beneficio(models.Model):
    nome = models.CharField(
        'Nome', 
        max_length=45, 
        blank=False, 
        null=False, 
        unique=True,
    )
    descricao_curta = models.CharField(
        'Descrição curta', 
        max_length=100, 
        blank=False, 
        null=False, 
        unique=True,
    )
    icon = models.ImageField(
        'Ícone',
        blank=True,
        null=True,
        unique=False
    )
    displayable_on_homepage = models.BooleanField(
        'Visível na página inicial',
        default=False,
        null=False,
        blank=False
    )

    class Meta:
        verbose_name = 'Benefício'

    def clean(self) -> None:
        super().clean()
        self.error_messages = {}
        self._validate_icon_size()
        
        if self.error_messages:
            raise ValidationError(self.error_messages)            

    def _validate_icon_size(self):
        if self.icon:
            if self.icon.width > 64 or self.icon.height > 64:
                self.error_messages['icon'] = 'O ícone deve ter tamanho 64x64.'

    def __str__(self) -> str:
        return self.nome


class Classe(models.Model):
    nome = models.CharField(
        'Classe', 
        max_length=15, 
        blank=False, 
        null=False, 
        unique=True,
        validators=[
            RegexValidator(r'^[\w ]+$', ClasseErrorMessages.INVALID_NAME)
        ]
    )

    def __str__(self) -> str:
        return self.nome


class Quarto(models.Model):
    classe = models.ForeignKey(
        Classe,
        on_delete=models.DO_NOTHING,
        related_name='quartos',
        related_query_name='quarto'
    )
    numero = models.CharField(
        'Número',
        blank=False,
        null=False,
        unique=True,
        max_length=4,
        validators=[
            RegexValidator(r"^\d{3}[A-Z]?$")
        ]
    )
    capacidade_adultos = models.PositiveSmallIntegerField(
        'Capacidade adultos',
        blank=False, 
        null=False, 
        default=1,
        validators=[
            MaxValueValidator(QuartoRules.MAX_ADULTS, QuartoErrorMessages.ADULTS_EXCEEDED),
            MinValueValidator(QuartoRules.MIN_ADULTS, QuartoErrorMessages.ADULTS_INSUFFICIENT),
        ]
    )
    capacidade_criancas = models.PositiveSmallIntegerField(
        'Capacidade crianças', 
        blank=False, 
        null=False, 
        default=1,
        validators=[
            MaxValueValidator(QuartoRules.MAX_CHILDREN, QuartoErrorMessages.CHILD_EXCEEDED),
            MinValueValidator(QuartoRules.MIN_CHILDREN, QuartoErrorMessages.CHILD_INSUFFICIENT),
        ]
    )
    tamanho = models.FloatField(
        'Tamanho m²', 
        blank=False, 
        null=False,
        validators=[
            MinValueValidator(QuartoRules.MIN_SIZE, QuartoErrorMessages.SIZE_INSUFFICIENT),
            MaxValueValidator(QuartoRules.MAX_SIZE, QuartoErrorMessages.SIZE_EXCEEDED),
        ]
    )
    preco_diaria = models.DecimalField(
        'Diária', 
        max_digits=10, 
        decimal_places=2, 
        blank=False, 
        null=False,
        validators=[
            MinValueValidator(QuartoRules.MIN_DAILY_PRICE, QuartoErrorMessages.PRICE_INSUFFICIENT),
            MaxValueValidator(QuartoRules.MAX_DAILY_PRICE, QuartoErrorMessages.PRICE_EXCEEDED),
        ]
    )
    beneficio = models.ManyToManyField(
        Beneficio, 
        related_name='quarto_beneficios', 
        related_query_name='quarto_beneficio',
        verbose_name='Benefícios'
    )
    disponivel = models.BooleanField(
        'Disponível',
        blank=False,
        null=False,
        default=True
    )
    image = models.ImageField(
        'Imagem', 
        upload_to='%Y-%m', 
        validators=[
            FileExtensionValidator(['jpg', 'png'], 'Somete jpg ou png'),
            validate_image_file_extension
        ],
        blank=True,
        null=True
    )
    short_desc = models.CharField(
        'Descrição curta',
        max_length=255,
        blank=False,
        null=False,
        unique=True,
    )
    long_desc = models.TextField(
        'Descrição longa',
        max_length=1000,
        null=True,
        blank=True
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_quartos',
        related_query_name='hotel_quarto'
    )

    class Meta:
        ordering = ['-disponivel']

    def clean(self) -> None:
        super().clean()
        error_messages = {}
        if self.image and not re.match(r'^(\w+/?-?)+\.(jpg|png)$', self.image.name):
            error_messages['image'] = QuartoErrorMessages.IMAGE_INVALID_NAME
            
        if error_messages: raise ValidationError(error_messages)

    def __str__(self) -> str:
        return f'Nº{self.numero} {self.classe}'

    def daily_price_formatted(self):
        return f'R${self.preco_diaria:.2f}'
    
    daily_price_formatted.short_description = 'Preço da diária'
    
    @property
    def daily_price_in_cents(self) -> int:
        return int(self.preco_diaria * Decimal('100'))

    @staticmethod
    def resize_image(img_path, w, h=None):
        img = Image.open(img_path)
        original_w, original_h = img.size

        if h is None: h = round(w * original_h / original_w)
        if original_h <= h: return
        
        resized = img.resize((w, h), Image.Resampling.NEAREST)
        resized.save(img_path, optimize=True, quality=70)

        resized.close()
        img.close()

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        if self.image:
            self.resize_image(self.image.path, *QuartoRules.IMAGE_SIZE)


class Reserva(models.Model):
    check_in = models.DateField(
        'Check-in',
        blank=False,
        null=False,
    )
    checkout = models.DateField(
        'Check-out', 
        blank=False, 
        null=False,
    )
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.SET_NULL, 
        related_name='reserva_clientes', 
        related_query_name='reserva_cliente',
        null=True
    )
    quarto = models.ForeignKey(
        Quarto, 
        on_delete=models.SET_NULL, 
        related_name='reserva_quartos', 
        related_query_name='reserva_quarto',
        null=True,
        blank=True
    )
    observacoes = models.TextField(
        'Observações', 
        max_length=100, 
        blank=True,
        null=True,
        validators=[
            RegexValidator(r'[\w\s]*'),
        ]
    )
    custo =  models.DecimalField(
        'Valor da reserva', 
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(QuartoRules.MIN_DAILY_PRICE),
        ]
    )
    active = models.BooleanField(
        'Ativa',
        'ativa',
        null=False,
        blank=False,
        default=False,
    )
    STATUS_CHOICES = (
        ('I', 'iniciada'),
        ('P', 'processando'),
        ('A', 'ativa'),
        ('C', 'cancelada'),
        ('F', 'finalizada')
    )
    status = models.CharField(
        'Status',
        max_length=2,
        null=False,
        blank=False,
        choices=STATUS_CHOICES,
        default='I'
    )
    created_at = models.DateTimeField(
        'Criada em',
        null=False,
        blank=False,
        default=timezone.now
    )

    def __str__(self) -> str:
        return f'< {self.__class__.__name__}: {self.pk} >'
    
    def formatted_price(self):
        if isinstance(self.custo, int|float|Decimal):
            return f'R${self.custo:.2f}'
        raise AttributeError('Custo não foi persistido.')
    
    formatted_price.short_description = 'Valor da reserva'
    
    def calc_reservation_value(self) -> Decimal:
        """"calcula o valor da reserva atribuindo a model e retorna o valor 
        em centavos."""
        days = Decimal(str((self.checkout - self.check_in).days))
        value = self.quarto.preco_diaria * days
        return value

    def clean(self) -> None:
        super().clean()
        self.error_messages = {}
        self._validate_check_in()
        self._validate_room()
        
        if self.error_messages:
            raise ValidationError(self.error_messages)
    
    def _validate_check_in(self):
        if self.check_in < datetime.now().date():
           self.error_messages['check_in'] = ReservaErrorMessages.INVALID_CHECKIN_DATE

        elif self.check_in > ReservaRules.checkin_anticipation_offset():
           self.error_messages['check_in'] = ReservaErrorMessages.INVALID_CHECKIN_ANTICIPATION
        
        elif not ReservaRules.MIN_RESERVATION_DAYS <= self.reservation_days <= ReservaRules.MAX_RESERVATION_DAYS:
            self.error_messages['check_in'] = ReservaErrorMessages.INVALID_STAYED_DAYS

    def _validate_room(self):
        if self.quarto:
            if not self.quarto.disponivel and self.status == 'I':
                self.error_messages['quarto'] = ReservaErrorMessages.UNAVAILABLE_ROOM

    @property
    def reservation_days(self) -> int:
        return (self.checkout - self.check_in).days

    @property
    def coast_in_cents(self):
        return int(self.custo * Decimal('100'))
