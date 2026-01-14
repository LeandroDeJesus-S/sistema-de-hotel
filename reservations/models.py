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
from django.utils.translation import gettext_lazy as gtl

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

from .rules import BenefitRules, ReserveRules, RoomClassRules, RoomRules


class Benefit(models.Model):
    """benefícios ao qual um quarto possui"""

    name = models.CharField(
        gtl('Nome'),
        max_length=BenefitRules.NAME_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        validators=[
            RegexValidator(BenefitRules.NAME_PATTERN, BenefitErrorMessages.INVALID_PATTERN)
        ],
        help_text=gtl('Nome único do benefício oferecido pelo quarto'),
    )
    short_desc = models.CharField(
        gtl('Descrição curta'),
        max_length=BenefitRules.SHORT_DESC_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        help_text=gtl('Descrição breve do benefício (até 100 caracteres)'),
    )
    icon = models.ImageField(
        gtl('Ícone'),
        blank=True,
        null=True,
        unique=False,
        help_text=gtl('ícone com tamanho %(w)sx%(h)s')
        % {'w': BenefitRules.ICON_SIZE[0], 'h': BenefitRules.ICON_SIZE[1]},
        upload_to=BenefitRules.BENEFIT_ICON_UPLOAD_PATH,
        validators=[validate_benefit_icon],
    )
    displayable_on_homepage = models.BooleanField(
        gtl('Visível na página inicial'),
        default=False,
        null=False,
        blank=False,
        help_text=gtl('Se marcado, o benefício será exibido na página inicial'),
    )

    class Meta:
        verbose_name = 'Benefício'
        verbose_name_plural = 'Benefícios'

    def __str__(self) -> str:
        return str(self.name)


class Class(models.Model):
    """representa as classes para os quartos"""

    name = models.CharField(
        gtl('Classe'),
        max_length=RoomClassRules.MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        validators=[RegexValidator(r'^\w[\w ]*$', ClasseErrorMessages.INVALID_NAME)],
        help_text=gtl('Nome da classe do quarto (ex: Standard, Deluxe)'),
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
        help_text=gtl('Classe à qual o quarto pertence'),
    )
    number = models.CharField(
        gtl('Número'),
        blank=False,
        null=False,
        unique=True,
        max_length=RoomRules.NUMBER_MAX_LEN,
        validators=[
            RegexValidator(
                r'^\d{3}[A-Z]?$',
            )
        ],
        help_text=gtl('Número único do quarto (ex: 101, 102A, máximo %(max)s caracteres)')
        % {'max': RoomRules.NUMBER_MAX_LEN},
    )
    adults_capacity = models.PositiveSmallIntegerField(
        gtl('Capacidade de adultos'),
        blank=False,
        null=False,
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_ADULTS, RoomErrorMessages.ADULTS_EXCEEDED),
            MinValueValidator(RoomRules.MIN_ADULTS, RoomErrorMessages.ADULTS_INSUFFICIENT),
        ],
        help_text=gtl(
            'Número máximo de adultos que o quarto comporta (entre %(min)s e %(max)s)'
        )
        % {'min': RoomRules.MIN_ADULTS, 'max': RoomRules.MAX_ADULTS},
    )
    children_capacity = models.PositiveSmallIntegerField(
        gtl('Capacidade crianças'),
        blank=False,
        null=False,
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_CHILDREN, RoomErrorMessages.CHILD_EXCEEDED),
            MinValueValidator(RoomRules.MIN_CHILDREN, RoomErrorMessages.CHILD_INSUFFICIENT),
        ],
        help_text=gtl(
            'Número máximo de crianças que o quarto comporta (entre %(min)s e %(max)s)'
        )
        % {'min': RoomRules.MIN_CHILDREN, 'max': RoomRules.MAX_CHILDREN},
    )
    size = models.FloatField(
        gtl('Tamanho m²'),
        blank=False,
        null=False,
        validators=[
            MinValueValidator(RoomRules.MIN_SIZE, RoomErrorMessages.SIZE_INSUFFICIENT),
            MaxValueValidator(RoomRules.MAX_SIZE, RoomErrorMessages.SIZE_EXCEEDED),
        ],
        help_text=gtl('Tamanho do quarto em metros quadrados (entre %(min)s e %(max)s)')
        % {'min': RoomRules.MIN_SIZE, 'max': RoomRules.MAX_SIZE},
    )
    daily_price = models.DecimalField(
        gtl('Diária'),
        max_digits=RoomRules.DAILY_PRICE_MAX_DIGITS,
        decimal_places=RoomRules.DAILY_PRICE_DECIMAL_PLACES,
        blank=False,
        null=False,
        validators=[
            MinValueValidator(RoomRules.MIN_DAILY_PRICE, RoomErrorMessages.PRICE_INSUFFICIENT),
            MaxValueValidator(RoomRules.MAX_DAILY_PRICE, RoomErrorMessages.PRICE_EXCEEDED),
        ],
        help_text=gtl('Preço da diária em reais (entre %(min)s e %(max)s)')
        % {'min': RoomRules.MIN_DAILY_PRICE, 'max': RoomRules.MAX_DAILY_PRICE},
    )
    benefits = models.ManyToManyField(
        Benefit,
        related_name='room_benefits',
        related_query_name='room_benefit',
        verbose_name='Benefícios',
        help_text=gtl('Benefícios oferecidos por este quarto'),
    )
    available = models.BooleanField(
        gtl('Disponível'),
        blank=False,
        null=False,
        default=True,
        help_text=gtl('Se marcado, o quarto está disponível para reservas'),
    )
    image = models.ImageField(
        gtl('Imagem'),
        upload_to=RoomRules.IMAGE_UPLOAD_FORMAT,
        validators=[
            FileExtensionValidator(['jpg', 'png'], 'Somete jpg ou png'),
            validate_image_file_extension,
        ],
        blank=True,
        null=True,
        help_text=gtl('Imagem principal do quarto (formatos aceitos: JPG, PNG)'),
    )
    short_desc = models.CharField(
        gtl('Descrição curta'),
        max_length=RoomRules.SHORT_DESC_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        help_text=gtl('Descrição curta do quarto (até %(max)s caracteres)')
        % {'max': RoomRules.SHORT_DESC_MAX_LEN},
    )
    long_desc = models.TextField(
        gtl('Descrição longa'),
        max_length=RoomRules.LONG_DESC_MAX_LEN,
        null=True,
        blank=True,
        help_text=gtl('Descrição detalhada do quarto (até 1000 caracteres)'),
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_rooms',
        related_query_name='hotel_room',
        help_text=gtl('Hotel ao qual o quarto pertence'),
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
        gtl('Check-in'),
        blank=False,
        null=False,
        help_text=gtl('Data de check-in no formato DD/MM/AAAA'),
    )
    checkout = models.DateField(
        gtl('Check-out'),
        blank=False,
        null=False,
        help_text=gtl('Data de check-out no formato DD/MM/AAAA'),
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        related_name='reservation_clients',
        related_query_name='reservation_client',
        null=True,
        help_text=gtl('Cliente que fez a reserva'),
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        related_name='reservation_rooms',
        related_query_name='reservation_room',
        null=True,
        blank=True,
        help_text=gtl('Quarto reservado'),
    )
    observations = models.TextField(
        gtl('Observações'),
        max_length=ReserveRules.OBSERVATIONS_MAX_LEN,
        blank=True,
        validators=[
            RegexValidator(r'[\w\s]*'),
        ],
        help_text=gtl('Observações adicionais sobre a reserva (máximo %(max)s caracteres)')
        % {'max': ReserveRules.OBSERVATIONS_MAX_LEN},
    )
    amount = models.DecimalField(
        gtl('Valor total da reserva'),
        max_digits=ReserveRules.AMOUNT_MAX_DIGITS,
        decimal_places=ReserveRules.AMOUNT_DECIMAL_PLACES,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(RoomRules.MIN_DAILY_PRICE),
        ],
        help_text=gtl('Valor total calculado da reserva em reais'),
    )

    class Status(models.TextChoices):
        INITIALIZED = ReservationStatusEnum.INITIALIZED.value, 'iniciada'
        PROCESSING = ReservationStatusEnum.PROCESSING.value, 'processando'
        ACTIVE = ReservationStatusEnum.ACTIVE.value, 'ativa'
        CANCELLED = ReservationStatusEnum.CANCELLED.value, 'cancelada'
        FINISHED = ReservationStatusEnum.FINISHED.value, 'finalizada'
        SCHEDULED = ReservationStatusEnum.SCHEDULED.value, 'agendada'

    status = models.CharField(
        gtl('Status'),
        max_length=1,
        null=False,
        blank=False,
        choices=Status.choices,
        default=Status.INITIALIZED,
        help_text=gtl('Status atual da reserva'),
    )
    created_at = models.DateTimeField(
        gtl('Criada em'),
        null=False,
        blank=False,
        default=timezone.now,
        help_text=gtl('Data e hora da criação da reserva'),
    )
    cancelled_at = models.DateTimeField(
        gtl('Cancelada em'),
        null=True,
        blank=True,
        help_text=gtl('Data e hora do cancelamento, se aplicável'),
    )
    cancellation_reason = models.TextField(
        gtl('Motivo do cancelamento'),
        blank=True,
        help_text=gtl('Motivo do cancelamento da reserva'),
    )

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
