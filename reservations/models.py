import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
    validate_image_file_extension,
)
from django.db import models
from django.utils import timezone

from clients.models import Client
from home.models import Hotel
from reservations.domain import entities
from reservations.domain.value_objects import ReservationStatusEnum
from reservations.feedback_messages import (
    BenefitErrorMessages,
    ClasseErrorMessages,
    RoomErrorMessages,
)
from utils import support
from utils.adapters.image_validators import validate_benefit_icon
from utils.models.middleware import ResizeImageMiddleware, model_middleware

from .rules import BenefitRules, ReserveRules, RoomRules


class Benefit(models.Model):
    """benefícios ao qual um quarto possui"""

    name = models.CharField(
        'Nome',
        max_length=45,
        blank=False,
        null=False,
        unique=True,
        validators=[
            RegexValidator(BenefitRules.NAME_PATTERN, BenefitErrorMessages.INVALID_PATTERN)
        ],
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
        upload_to='benefits/icon',
        validators=[validate_benefit_icon],
    )
    displayable_on_homepage = models.BooleanField(
        'Visível na página inicial', default=False, null=False, blank=False
    )

    class Meta:
        verbose_name = 'Benefício'
        verbose_name_plural = 'Benefícios'

    def __str__(self) -> str:
        return str(self.name)


class Class(models.Model):
    """representa as classes para os quartos"""

    name = models.CharField(
        'Classe',
        max_length=15,
        blank=False,
        null=False,
        unique=True,
        validators=[RegexValidator(r'^\w[\w ]*$', ClasseErrorMessages.INVALID_NAME)],
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'


@model_middleware(
    ResizeImageMiddleware(
        field_name='image',
        w=RoomRules.IMAGE_SIZE[0],
        h=RoomRules.IMAGE_SIZE[1],
        create_only=False,
    )
)
class Room(models.Model):
    """representa os quartos de um determinado hotel"""

    room_class = models.ForeignKey(
        Class,
        on_delete=models.DO_NOTHING,
        related_name='class_quartos',
        related_query_name='class_room',
    )
    number = models.CharField(
        'Número',
        blank=False,
        null=False,
        unique=True,
        max_length=4,
        validators=[
            RegexValidator(
                r'^\d{3}[A-Z]?$',
            )
        ],
    )
    adults_capacity = models.PositiveSmallIntegerField(
        'Capacidade de adultos',
        blank=False,
        null=False,
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_ADULTS, RoomErrorMessages.ADULTS_EXCEEDED),
            MinValueValidator(RoomRules.MIN_ADULTS, RoomErrorMessages.ADULTS_INSUFFICIENT),
        ],
    )
    children_capacity = models.PositiveSmallIntegerField(
        'Capacidade crianças',
        blank=False,
        null=False,
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_CHILDREN, RoomErrorMessages.CHILD_EXCEEDED),
            MinValueValidator(RoomRules.MIN_CHILDREN, RoomErrorMessages.CHILD_INSUFFICIENT),
        ],
    )
    size = models.FloatField(
        'Tamanho m²',
        blank=False,
        null=False,
        validators=[
            MinValueValidator(RoomRules.MIN_SIZE, RoomErrorMessages.SIZE_INSUFFICIENT),
            MaxValueValidator(RoomRules.MAX_SIZE, RoomErrorMessages.SIZE_EXCEEDED),
        ],
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
        ],
    )
    benefits = models.ManyToManyField(
        Benefit,
        related_name='room_benefits',
        related_query_name='room_benefit',
        verbose_name='Benefícios',
    )
    available = models.BooleanField('Disponível', blank=False, null=False, default=True)
    image = models.ImageField(
        'Imagem',
        upload_to='%Y-%m',
        validators=[
            FileExtensionValidator(['jpg', 'png'], 'Somete jpg ou png'),
            validate_image_file_extension,
        ],
        blank=True,
        null=True,
    )
    short_desc = models.CharField(
        'Descrição curta',
        max_length=255,
        blank=False,
        null=False,
        unique=True,
    )
    long_desc = models.TextField('Descrição longa', max_length=1000, null=True, blank=True)
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_rooms',
        related_query_name='hotel_room',
    )

    class Meta:
        verbose_name = 'Quarto'
        verbose_name_plural = 'Quartos'
        ordering = ['-available']

    def clean(self) -> None:
        super().clean()
        error_messages = {}
        if self.image and not re.match(r'^[\w\-\/]+\.(jpg|png)$', self.image.name):
            error_messages['image'] = RoomErrorMessages.IMAGE_INVALID_NAME

        if error_messages:
            raise ValidationError(error_messages)

    def __str__(self) -> str:
        return f'Nº{self.number} {self.room_class}'

    def daily_price_formatted(self):
        """valor da diária do quarto no formato R$xn.xx"""
        return f'R${self.daily_price:.2f}'

    daily_price_formatted.short_description = 'Preço da diária'  # type: ignore[attr-defined]

    @property
    def daily_price_in_cents(self) -> int:
        """retorna o valor da diária em centavos para auxilio
        com api do stripe"""
        return int(self.daily_price * Decimal('100'))


class Reservation(models.Model):
    """representa o registro de uma reserva"""

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

        constraints = [
            models.CheckConstraint(
                name='checkin_check',
                check=models.Q(checkin__lte=models.F('checkout')),
            ),
            models.CheckConstraint(
                name='min_stayed_days',
                check=models.Q(
                    checkout__gte=models.F('checkin')
                    + timezone.timedelta(days=ReserveRules.MIN_RESERVATION_DAYS)
                ),
            ),
            models.CheckConstraint(
                name='max_stayed_days',
                check=models.Q(
                    checkout__lte=models.F('checkin')
                    + timezone.timedelta(days=ReserveRules.MAX_RESERVATION_DAYS)
                ),
            ),
        ]

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
        null=True,
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        related_name='reservation_rooms',
        related_query_name='reservation_room',
        null=True,
        blank=True,
    )
    observations = models.TextField(
        'Observações',
        max_length=100,
        blank=True,
        validators=[
            RegexValidator(r'[\w\s]*'),
        ],
    )
    amount = models.DecimalField(
        'Valor total da reserva',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(RoomRules.MIN_DAILY_PRICE),
        ],
    )

    class Status(models.TextChoices):
        INITIALIZED = ReservationStatusEnum.INITIALIZED.value, 'iniciada'
        PROCESSING = ReservationStatusEnum.PROCESSING.value, 'processando'
        ACTIVE = ReservationStatusEnum.ACTIVE.value, 'ativa'
        CANCELLED = ReservationStatusEnum.CANCELLED.value, 'cancelada'
        FINISHED = ReservationStatusEnum.FINISHED.value, 'finalizada'
        SCHEDULED = ReservationStatusEnum.SCHEDULED.value, 'agendada'

    status = models.CharField(
        'Status',
        max_length=1,
        null=False,
        blank=False,
        choices=Status.choices,
        default=Status.INITIALIZED,
    )
    created_at = models.DateTimeField(
        'Criada em', null=False, blank=False, default=timezone.now
    )
    cancelled_at = models.DateTimeField('Cancelada em', null=True, blank=True)
    cancellation_reason = models.TextField('Motivo do cancelamento', blank=True)

    def __str__(self) -> str:
        return f'<{self.__class__.__name__}: {self.pk}>'

    def formatted_price(self) -> str:
        """valor total da reserva no formato R$xn.xx

        Raises:
            AttributeError: se chamado antes de `amount` ser persistido
        """
        if isinstance(self.amount, int | float | Decimal):
            return f'R${self.amount:.2f}'
        raise AttributeError('Custo não foi persistido.')

    formatted_price.short_description = 'Valor total da reserva'  # type: ignore[attr-defined]

    def calc_reservation_value(self) -> Decimal:
        """ "calcula o valor da reserva atribuindo a model e retorna o valor
        em centavos."""
        days = Decimal(str((self.checkout - self.checkin).days))
        value = self.room.daily_price * days
        return Decimal(value)

    def clean(self) -> None:
        super().clean()
        result = support.model_to_entity(self, entities.Reservation)
        if result.is_err():
            res_err = result.unwrap_err()
            err = res_err.src_error or res_err
            raise ValidationError(getattr(err, 'msg', str(err)))

    @property
    def reservation_days(self) -> int:
        """retorna a quantidade dias da reserva"""
        return int((self.checkout - self.checkin).days)

    @property
    def coast_in_cents(self):
        """custo da reserva em centavos"""
        return int(self.amount * Decimal('100'))
