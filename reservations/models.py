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

from clients.models import Client
from home.models import Hotel
from utils.supportmodels import (
    ReserveRules, 
    ReserveErrorMessages,
    RoomRules,
    ClasseErrorMessages,
    RoomErrorMessages,
    BenefitRules,
    BenefitErrorMessages
)
from utils import support


class Benefit(models.Model):
    """benefícios ao qual um quarto possui"""
    name = models.CharField(
        'Nome', 
        max_length=45, 
        blank=False, 
        null=False, 
        unique=True,
    )
    short_desc = models.CharField(
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
        unique=False,
        help_text='ícone com tamanho 64x64',
        upload_to='benefits/icon'
    )
    displayable_on_homepage = models.BooleanField(
        'Visível na página inicial',
        default=False,
        null=False,
        blank=False
    )

    class Meta:
        verbose_name = 'Benefício'
        verbose_name_plural = 'Benefícios'

    def clean(self) -> None:
        super().clean()
        self.error_messages = {}
        self._validate_icon_size()
        
        if self.error_messages:
            raise ValidationError(self.error_messages)            

    def _validate_icon_size(self):
        """valida se o ícone possui dimensão maxima de até 64x64"""
        if self.icon:
            w, h = BenefitRules.ICON_SIZE
            if self.icon.width > w or self.icon.height > h:
                self.error_messages['icon'] = BenefitErrorMessages.INVALID_ICON_SIZE

    def __str__(self) -> str:
        return self.name


class Class(models.Model):
    """representa as classes para os quartos"""
    name = models.CharField(
        'Classe', 
        max_length=15, 
        blank=False, 
        null=False, 
        unique=True,
        validators=[
            RegexValidator(r'^\w[\w ]*$', ClasseErrorMessages.INVALID_NAME)
        ]
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'


class Room(models.Model):
    """representa os quartos de um determinado hotel"""
    room_class = models.ForeignKey(
        Class,
        on_delete=models.DO_NOTHING,
        related_name='class_quartos',
        related_query_name='class_room'
    )
    number = models.CharField(
        'Número',
        blank=False,
        null=False,
        unique=True,
        max_length=4,
        validators=[
            RegexValidator(r"^\d{3}[A-Z]?$", )
        ]
    )
    adult_capacity = models.PositiveSmallIntegerField(
        'Capacidade de adultos',
        blank=False, 
        null=False, 
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_ADULTS, RoomErrorMessages.ADULTS_EXCEEDED),
            MinValueValidator(RoomRules.MIN_ADULTS, RoomErrorMessages.ADULTS_INSUFFICIENT),
        ]
    )
    child_capacity = models.PositiveSmallIntegerField(
        'Capacidade crianças', 
        blank=False, 
        null=False, 
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_CHILDREN, RoomErrorMessages.CHILD_EXCEEDED),
            MinValueValidator(RoomRules.MIN_CHILDREN, RoomErrorMessages.CHILD_INSUFFICIENT),
        ]
    )
    size = models.FloatField(
        'Tamanho m²', 
        blank=False, 
        null=False,
        validators=[
            MinValueValidator(RoomRules.MIN_SIZE, RoomErrorMessages.SIZE_INSUFFICIENT),
            MaxValueValidator(RoomRules.MAX_SIZE, RoomErrorMessages.SIZE_EXCEEDED),
        ]
    )
    daily_price = models.DecimalField(
        'Diária', 
        max_digits=10, 
        decimal_places=2, 
        blank=False, 
        null=False,
        validators=[
            MinValueValidator(RoomRules.MIN_DAILY_PRICE, RoomErrorMessages.PRICE_INSUFFICIENT),
            MaxValueValidator(RoomRules.MAX_DAILY_PRICE, RoomErrorMessages.PRICE_EXCEEDED),
        ]
    )
    benefit = models.ManyToManyField(
        Benefit, 
        related_name='room_benefits', 
        related_query_name='room_benefit',
        verbose_name='Benefícios'
    )
    available = models.BooleanField(
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
        related_name='hotel_rooms',
        related_query_name='hotel_room'
    )

    class Meta:
        verbose_name = 'Quarto'
        verbose_name_plural = 'Quartos'
        ordering = ['-available']

    def clean(self) -> None:
        super().clean()
        error_messages = {}
        if self.image and not re.match(r'^(\w+/?-?)+\.(jpg|png)$', self.image.name):
            error_messages['image'] = RoomErrorMessages.IMAGE_INVALID_NAME
            
        if error_messages: raise ValidationError(error_messages)

    def __str__(self) -> str:
        return f'Nº{self.number} {self.room_class}'

    def daily_price_formatted(self):
        """valor da diária do quarto no formato R$xn.xx"""
        return f'R${self.daily_price:.2f}'
    
    daily_price_formatted.short_description = 'Preço da diária'
    
    @property
    def daily_price_in_cents(self) -> int:
        """retorna o valor da diária em centavos para auxilio
        com api do stripe"""
        return int(self.daily_price * Decimal('100'))

    # @staticmethod
    # def resize_image(img_path, w, h=None):
    #     """redimensiona imagem com tamanhos expecificados

    #     Args:
    #         img_path (Any): caminho da imagem
    #         w (int): largura da imagem
    #         h (int, optional): altura da imagem. Defaults to None.
    #     """
    #     img = Image.open(img_path)
    #     original_w, original_h = img.size

    #     if h is None: h = round(w * original_h / original_w)
    #     if original_h <= h: h = original_h
        
    #     resized = img.resize((w, h), Image.Resampling.NEAREST)
    #     resized.save(img_path, optimize=True, quality=70)

    #     resized.close()
    #     img.close()

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        if self.image:
            support.resize_image(self.image.path, *RoomRules.IMAGE_SIZE)


class Reservation(models.Model):
    """representa o registro de uma reserva"""
    checkin = models.DateField(
        'Check-in',
        blank=False,
        null=False,
    )
    checkout = models.DateField(
        'Check-out', 
        blank=False, 
        null=False,
    )
    client = models.ForeignKey(
        Client, 
        on_delete=models.SET_NULL, 
        related_name='reservation_clients', 
        related_query_name='reservation_client',
        null=True
    )
    room = models.ForeignKey(
        Room, 
        on_delete=models.SET_NULL, 
        related_name='reservation_rooms', 
        related_query_name='reservation_room',
        null=True,
        blank=True
    )
    observations = models.TextField(
        'Observações', 
        max_length=100, 
        blank=True,
        null=True,
        validators=[
            RegexValidator(r'[\w\s]*'),
        ]
    )
    amount =  models.DecimalField(
        'Valor total da reserva', 
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(RoomRules.MIN_DAILY_PRICE),
        ]
    )
    active = models.BooleanField(
        'Ativa',
        null=False,
        blank=False,
        default=False,
    )
    STATUS_CHOICES = (
        ('I', 'iniciada'),
        ('P', 'processando'),
        ('A', 'ativa'),
        ('C', 'cancelada'),
        ('F', 'finalizada'),
        ('S', 'agendada')
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
        return f'<{self.__class__.__name__}: {self.pk}>'
    
    def formatted_price(self) -> str:
        """valor total da reserva no formato R$xn.xx

        Raises:
            AttributeError: se chamado antes de `amount` ser persistido
        """
        if isinstance(self.amount, int|float|Decimal):
            return f'R${self.amount:.2f}'
        raise AttributeError('Custo não foi persistido.')
    
    formatted_price.short_description = 'Valor total da reserva'
    
    def calc_reservation_value(self) -> Decimal:
        """"calcula o valor da reserva atribuindo a model e retorna o valor 
        em centavos."""
        days = Decimal(str((self.checkout - self.checkin).days))
        value = self.room.daily_price * days
        return value

    def clean(self) -> None:
        super().clean()
        self.error_messages = {}
        if self.status == 'I':
            self._validate_date_availability(self.error_messages, 'checkin')
            self._validate_check_in()
            self._validate_room()
        
        if self.error_messages:
            raise ValidationError(self.error_messages)
    
    @classmethod
    def get_free_dates(cls, reservations) -> str:
        """retorna as datas de reserva livres para um conjunto
        de reservas, considerando os períodos de gap entre as datas com 
        número de dias de diferença maior que 1
        Ex.:
        >>> reservations = Reservation.objects.filter(status__in=['A', 'S'])
        >>> [(r.checkin.strftime('%d/%m/%Y'), r.checkout.strftime('%d/%m/%Y')) for r in reservations]
        >>> ('01/01/2024', '02/01/2024'), ('05/01/2024', '07/01/2024')
        >>> Reservation.get_free_dates(reservations)
        >>> '02/01/2024 a 04/01/2024, e 07/01/2024 para frente.'
        """
        fmt_date = lambda d: d.strftime('%d/%m/%Y')
        dates = []
        lst = None
        for reserva in reservations:
            if lst is None:
                lst = reserva
                continue 

            if (reserva.checkin - lst.checkout).days >= 1:
                start, end = fmt_date(lst.checkout), fmt_date(reserva.checkin - timezone.timedelta(days=1))
                dates.append(f'{start} a {end}')
            
            lst = reserva
        dates.append(f'e {fmt_date(reserva.checkout)} para frente.')
        return ', '.join(dates)

    @classmethod
    def available_dates(cls, room) -> str:
        """retorna as datas de reservas disponíveis para o quarto especificado
        considerando reserva ativa e agendamentos, chamando Reservation.get_free_dates
        para reservas agendadas ou ativas

        Args:
            room (reservations.models.Quarto): uma instancia da model Quarto

        Returns:
            str: string com msg de datas disponíveis (e.g d/m/Y a d/m/Y, e d/m/Y para frente)
        """
        reservas = Reservation.objects.filter(
            room=room,
            status__in=['A', 'S']
        )
        return cls.get_free_dates(reservas)
        
    def _validate_date_availability(self, msg_dict, k) -> bool:
        """verifica se a data da reserva sobrepõe um reserva ativa ou agendada"""
        reservations = Reservation.objects.filter(
            room=self.room, 
            checkout__gt=self.checkin,
            checkin__lte=self.checkout,
            status__in=['A', 'S']
        )
        if reservations.exists():
            dates = self.get_free_dates(reservations)
            msg = ReserveErrorMessages.UNAVAILABLE_DATE.format_map({'dates': dates})
            msg_dict[k] = msg
    
    def _validate_check_in(self):
        """realiza as validações relacionadas ao check-in"""
        if self.checkin < datetime.now().date():
           self.error_messages['checkin'] = ReserveErrorMessages.INVALID_CHECKIN_DATE

        elif self.checkin > ReserveRules.checkin_anticipation_offset():
           self.error_messages['checkin'] = ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION
        
        elif not ReserveRules.MIN_RESERVATION_DAYS <= self.reservation_days <= ReserveRules.MAX_RESERVATION_DAYS:
            self.error_messages['checkin'] = ReserveErrorMessages.INVALID_STAYED_DAYS

    def _validate_room(self):
        """realiza as validações relacionadas ao quarto"""
        if not self.room.available:
            self.error_messages['room'] = ReserveErrorMessages.UNAVAILABLE_ROOM

    @property
    def reservation_days(self) -> int:
        """retorna a quantidade dias da reserva"""
        return (self.checkout - self.checkin).days

    @property
    def coast_in_cents(self):
        """custo da reserva em centavos"""
        return int(self.amount * Decimal('100'))

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
