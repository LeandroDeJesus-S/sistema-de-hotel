from datetime import datetime, timedelta, timezone

from pydantic import Field, model_validator

from base.entity import BaseEntity
from clients.domain.entities import Client
from home.domain.entities import Hotel
from reservations.domain.value_objects import (
    AdultsCapacity,
    BenefitIcon,
    BenefitName,
    BenefitShortDesc,
    ChildrenCapacity,
    Currency,
    PriceValue,
    ReservationObservations,
    ReservationStatus,
    RoomClassName,
    RoomLongDesc,
    RoomShortDesc,
    RoomSize,
)
from reservations.feedback_messages import (
    BenefitErrorMessages,
    ClasseErrorMessages,
    ReservationMessages,
    ReserveErrorMessages,
    RoomErrorMessages,
)
from reservations.rules import ReserveRules
from utils.decorators import ensure_result

from .value_objects import CheckInOut, ReservationStatusEnum, RoomNumber


class Benefit(BaseEntity):
    """Represents a benefit from a room.

    Attributes:
            name: BenefitName
            icon: BenefitIcon
            short_desc: BenefitShortDesc"""

    _messages = {
        'icon': {
            'value_error': BenefitErrorMessages.INVALID_ICON_SIZE,
            'string_too_short': BenefitErrorMessages.ICON_EMPTY,
        },
        'name': {
            'string_too_short': BenefitErrorMessages.NAME_EMPTY,
        },
        'short_desc': {
            'string_too_short': BenefitErrorMessages.SHORT_DESC_EMPTY,
        },
    }
    name: BenefitName
    icon: BenefitIcon
    short_desc: BenefitShortDesc
    id: int | None = None

    def __str__(self) -> str:
        return self.name


class Price(BaseEntity):
    """Represents a price for a room in a specific currency.

    Attributes:
        currency: Currency
        value: PriceValue
        active: bool
    """

    currency: Currency
    value: PriceValue
    active: bool
    id: int | None = None


class RoomClass(BaseEntity):
    """Represents a room class from the hotel.

    Attributes:
        name: RoomClassName
    """

    _messages = {
        'name': {
            'value_error': ClasseErrorMessages.INVALID_NAME,
            'string_too_short': ClasseErrorMessages.NAME_EMPTY,
        },
    }
    name: RoomClassName
    id: int | None = None

    def __str__(self) -> str:
        return self.name


class Room(BaseEntity):
    """Represents a room from the hotel.

    Attributes:
        number: RoomNumber
        adults_capacity: int
        children_capacity: int
        size: int
        prices: list[Price]
        available: bool
        image: str
        short_desc: str
        long_desc: str
        benefits: list[Benefit]
        room_class: RoomClass
        hotel: Hotel
    """

    _messages = {
        'adults_capacity': {
            'greater_than_equal': RoomErrorMessages.ADULTS_INSUFFICIENT,
            'less_than_equal': RoomErrorMessages.ADULTS_EXCEEDED,
        },
        'children_capacity': {
            'greater_than_equal': RoomErrorMessages.CHILD_INSUFFICIENT,
            'less_than_equal': RoomErrorMessages.CHILD_EXCEEDED,
        },
        'size': {
            'greater_than_equal': RoomErrorMessages.SIZE_INSUFFICIENT,
            'less_than_equal': RoomErrorMessages.SIZE_EXCEEDED,
        },
        'image': {
            'value_error': RoomErrorMessages.IMAGE_INVALID_NAME,
        },
        'short_desc': {
            'value_error': RoomErrorMessages.SHORT_DESC_INVALID,
        },
    }
    number: RoomNumber
    adults_capacity: AdultsCapacity
    children_capacity: ChildrenCapacity
    size: RoomSize
    prices: list[Price] = []
    available: bool = True
    image: str = ''
    short_desc: RoomShortDesc
    long_desc: RoomLongDesc

    benefits: list[Benefit] = []
    room_class: RoomClass
    hotel: Hotel
    id: int | None = None

    def __str__(self) -> str:
        return f'{self.number} - {self.room_class.name}'


class Reservation(BaseEntity):
    """Represents a reservation.

    Attributes:
        checkin: date
        checkout: date
        client: Client
        room: Room
        observations: str
        currency: Currency
        price: PriceValue
        status: ReservationStatus
        created_at: datetime
    """

    _messages = {
        'checkin': {
            'value_error': ReserveErrorMessages.INVALID_CHECKIN_DATE,
        },
        'checkout': {
            'value_error': ReservationMessages.INVALID_DATE_RANGE,
        },
        'room': {
            'value_error': ReserveErrorMessages.INVALID_ROOM_CHOICE,
        },
    }
    checkin: CheckInOut
    checkout: CheckInOut
    client: Client
    room: Room
    observations: ReservationObservations
    currency: Currency
    price: PriceValue
    status: ReservationStatus = ReservationStatusEnum.INITIALIZED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str = ''

    @ensure_result
    def reservation_days(self) -> int:
        """Returns the reservation stayed period"""
        return (self.checkout - self.checkin).days  # type: ignore

    @model_validator(mode='after')
    def validate_dates(self):
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

        if self.id is None and self.checkin < now - timedelta(minutes=1):
            raise ValueError(ReserveErrorMessages.INVALID_CHECKIN_DATE)

        if self.id is None and self.checkin > ReserveRules.checkin_anticipation_offset():
            raise ValueError(ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION)

        if self.checkin > self.checkout:
            raise ValueError(ReserveErrorMessages.INVALID_CHECKIN_DATE)

        stayed_days = (self.checkout - self.checkin).days
        if not (
            ReserveRules.MIN_RESERVATION_DAYS
            <= stayed_days
            <= ReserveRules.MAX_RESERVATION_DAYS
        ):
            raise ValueError(ReserveErrorMessages.INVALID_STAYED_DAYS)

        return self

    def __str__(self) -> str:
        return f'{self.checkin} - {self.checkout}'
