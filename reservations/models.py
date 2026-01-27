import re

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
    """Benefits that a room has"""

    name = models.CharField(
        gtl('Name'),
        max_length=BenefitRules.NAME_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        validators=[
            RegexValidator(BenefitRules.NAME_PATTERN, BenefitErrorMessages.INVALID_PATTERN)
        ],
        help_text=gtl('Unique name of the benefit offered by the room'),
    )
    short_desc = models.CharField(
        gtl('Short description'),
        max_length=BenefitRules.SHORT_DESC_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        help_text=gtl('Brief description of the benefit (up to 100 characters)'),
    )
    icon = models.ImageField(
        gtl('Icon'),
        blank=True,
        null=True,
        unique=False,
        help_text=gtl('icon with size %(w)sx%(h)s')
        % {'w': BenefitRules.ICON_SIZE[0], 'h': BenefitRules.ICON_SIZE[1]},
        upload_to=BenefitRules.BENEFIT_ICON_UPLOAD_PATH,
        validators=[validate_benefit_icon],
    )
    displayable_on_homepage = models.BooleanField(
        gtl('Visible on homepage'),
        default=False,
        null=False,
        blank=False,
        help_text=gtl('If checked, the benefit will be displayed on the homepage'),
    )

    class Meta:
        verbose_name = 'Benefit'
        verbose_name_plural = 'Benefits'

    def __str__(self) -> str:
        return str(self.name)


class Price(models.Model):
    """Represents a price for a room in a specific currency."""

    currency = models.CharField(
        gtl('Currency'),
        max_length=3,
        blank=False,
        null=False,
        validators=[RegexValidator(r'^[a-z]{3}$', 'Currency must be 3 lowercase letters')],
        help_text=gtl('Currency code in lowercase ISO 4217 format (e.g., usd, eur)'),
    )
    value = models.PositiveIntegerField(
        gtl('Value'),
        blank=False,
        null=False,
        help_text=gtl('Price value in cents'),
    )
    active = models.BooleanField(
        gtl('Active'),
        default=True,
        null=False,
        blank=False,
        help_text=gtl('Whether this price is available for use'),
    )

    class Meta:
        verbose_name = 'Price'
        verbose_name_plural = 'Prices'

    def __str__(self) -> str:
        return f'{self.currency.upper()} {self.value / 100:.2f}'


class Class(models.Model):
    """Represents the classes for the rooms"""

    name = models.CharField(
        gtl('Class'),
        max_length=RoomClassRules.MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        validators=[RegexValidator(r'^\w[\w ]*$', ClasseErrorMessages.INVALID_NAME)],
        help_text=gtl('Room class name (e.g., Standard, Deluxe)'),
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = 'Class'
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
    """Represents the rooms of a given hotel"""

    room_class = models.ForeignKey(
        Class,
        on_delete=models.DO_NOTHING,
        related_name='class_quartos',
        related_query_name='class_room',
        help_text=gtl('Class to which the room belongs'),
    )
    number = models.CharField(
        gtl('Number'),
        blank=False,
        null=False,
        unique=True,
        max_length=RoomRules.NUMBER_MAX_LEN,
        validators=[
            RegexValidator(
                r'^\d{3}[A-Z]?$',
            )
        ],
        help_text=gtl('Unique room number (e.g., 101, 102A, maximum %(max)s characters)')
        % {'max': RoomRules.NUMBER_MAX_LEN},
    )
    adults_capacity = models.PositiveSmallIntegerField(
        gtl('Adults capacity'),
        blank=False,
        null=False,
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_ADULTS, RoomErrorMessages.ADULTS_EXCEEDED),
            MinValueValidator(RoomRules.MIN_ADULTS, RoomErrorMessages.ADULTS_INSUFFICIENT),
        ],
        help_text=gtl(
            'Maximum number of adults the room can accommodate (between %(min)s and %(max)s)'
        )
        % {'min': RoomRules.MIN_ADULTS, 'max': RoomRules.MAX_ADULTS},
    )
    children_capacity = models.PositiveSmallIntegerField(
        gtl('Children capacity'),
        blank=False,
        null=False,
        default=1,
        validators=[
            MaxValueValidator(RoomRules.MAX_CHILDREN, RoomErrorMessages.CHILD_EXCEEDED),
            MinValueValidator(RoomRules.MIN_CHILDREN, RoomErrorMessages.CHILD_INSUFFICIENT),
        ],
        help_text=gtl(
            'Maximum number of children the room can accommodate (between %(min)s and %(max)s)'
        )
        % {'min': RoomRules.MIN_CHILDREN, 'max': RoomRules.MAX_CHILDREN},
    )
    size = models.FloatField(
        gtl('Size m²'),
        blank=False,
        null=False,
        validators=[
            MinValueValidator(RoomRules.MIN_SIZE, RoomErrorMessages.SIZE_INSUFFICIENT),
            MaxValueValidator(RoomRules.MAX_SIZE, RoomErrorMessages.SIZE_EXCEEDED),
        ],
        help_text=gtl('Room size in square meters (between %(min)s and %(max)s)')
        % {'min': RoomRules.MIN_SIZE, 'max': RoomRules.MAX_SIZE},
    )
    prices = models.ManyToManyField(
        Price,
        related_name='room_prices',
        blank=True,
        help_text=gtl('Prices for this room in different currencies'),
    )
    benefits = models.ManyToManyField(
        Benefit,
        related_name='room_benefits',
        related_query_name='room_benefit',
        verbose_name='Benefits',
        help_text=gtl('Benefits offered by this room'),
    )
    available = models.BooleanField(
        gtl('Available'),
        blank=False,
        null=False,
        default=True,
        help_text=gtl('If checked, the room is available for reservations'),
    )
    image = models.ImageField(
        gtl('Image'),
        upload_to=RoomRules.IMAGE_UPLOAD_FORMAT,
        validators=[
            FileExtensionValidator(['jpg', 'png'], 'Only jpg or png'),
            validate_image_file_extension,
        ],
        blank=True,
        null=True,
        help_text=gtl('Main room image (accepted formats: JPG, PNG)'),
    )
    short_desc = models.CharField(
        gtl('Short description'),
        max_length=RoomRules.SHORT_DESC_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        help_text=gtl('Short description of the room (up to %(max)s characters)')
        % {'max': RoomRules.SHORT_DESC_MAX_LEN},
    )
    long_desc = models.TextField(
        gtl('Long description'),
        max_length=RoomRules.LONG_DESC_MAX_LEN,
        null=True,
        blank=True,
        help_text=gtl('Detailed description of the room (up to 1000 characters)'),
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_rooms',
        related_query_name='hotel_room',
        help_text=gtl('Hotel to which the room belongs'),
    )

    class Meta:
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'
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


class Reservation(models.Model):
    """Represents the record of a reservation"""

    class Meta:
        verbose_name = 'Reservation'
        verbose_name_plural = 'Reservations'

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

    checkin = models.DateTimeField(
        gtl('Check-in'),
        blank=False,
        null=False,
        help_text=gtl('Check-in date and time in YYYY-MM-DD HH:MM:SS format'),
    )
    checkout = models.DateTimeField(
        gtl('Check-out'),
        blank=False,
        null=False,
        help_text=gtl('Check-out date and time in YYYY-MM-DD HH:MM:SS format'),
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        related_name='reservation_clients',
        related_query_name='reservation_client',
        null=True,
        help_text=gtl('Client who made the reservation'),
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        related_name='reservation_rooms',
        related_query_name='reservation_room',
        null=True,
        blank=True,
        help_text=gtl('Reserved room'),
    )
    observations = models.TextField(
        gtl('Observations'),
        max_length=ReserveRules.OBSERVATIONS_MAX_LEN,
        blank=True,
        validators=[
            RegexValidator(r'[\w\s]*'),
        ],
        help_text=gtl(
            'Additional observations about the reservation (maximum %(max)s characters)'
        )
        % {'max': ReserveRules.OBSERVATIONS_MAX_LEN},
    )
    currency = models.CharField(
        gtl('Currency'),
        max_length=10,
        choices=[('usd', gtl('USD')), ('brl', gtl('BRL'))],
        default='usd',
        null=True,
        blank=True,
        help_text=gtl('Currency for the reservation'),
    )
    price = models.PositiveIntegerField(
        gtl('Price'),
        null=True,
        blank=True,
        help_text=gtl('Total reservation price in cents'),
    )

    class Status(models.TextChoices):
        INITIALIZED = ReservationStatusEnum.INITIALIZED.value, 'initialized'
        PROCESSING = ReservationStatusEnum.PROCESSING.value, 'processing'
        ACTIVE = ReservationStatusEnum.ACTIVE.value, 'active'
        CANCELLED = ReservationStatusEnum.CANCELLED.value, 'cancelled'
        FINISHED = ReservationStatusEnum.FINISHED.value, 'finished'
        SCHEDULED = ReservationStatusEnum.SCHEDULED.value, 'scheduled'

    status = models.CharField(
        gtl('Status'),
        max_length=1,
        null=False,
        blank=False,
        choices=Status.choices,
        default=Status.INITIALIZED,
        help_text=gtl('Current reservation status'),
    )
    created_at = models.DateTimeField(
        gtl('Created at'),
        null=False,
        blank=False,
        default=timezone.now,
        help_text=gtl('Date and time of reservation creation'),
    )
    cancelled_at = models.DateTimeField(
        gtl('Cancelled at'),
        null=True,
        blank=True,
        help_text=gtl('Date and time of cancellation, if applicable'),
    )
    cancellation_reason = models.TextField(
        gtl('Cancellation reason'),
        blank=True,
        help_text=gtl('Reason for reservation cancellation'),
    )

    def __str__(self) -> str:
        return f'<{self.__class__.__name__}: {self.pk}>'

    def formatted_price(self) -> str:
        """Total reservation value in CUR X.XX format"""
        if self.price is not None:
            return f'{self.currency.upper()} {self.price / 100:.2f}'
        return 'Price not calculated'

    def calc_reservation_value(self) -> int:
        """Calculates the reservation value based on room price and duration."""
        days = (self.checkout - self.checkin).days
        room_price = self.room.prices.filter(currency=self.currency, active=True).first()
        if room_price:
            return int(room_price.value * days)
        return 0

    def clean(self) -> None:
        super().clean()
        result = support.model_to_entity(self, entities.Reservation)
        if result.is_err():
            res_err = result.unwrap_err()
            err = res_err.src_error or res_err
            raise ValidationError(getattr(err, 'msg', str(err)))
