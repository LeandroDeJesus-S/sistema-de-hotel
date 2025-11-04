from datetime import date, datetime, timezone
from decimal import Decimal

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
    DailyPrice,
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


class Room(BaseEntity):
    """Represents a room from the hotel.

    Attributes:
        number: RoomNumber
        adults_capacity: int
        children_capacity: int
        size: int
        daily_price: int
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
        'daily_price': {
            'greater_than_equal': RoomErrorMessages.PRICE_INSUFFICIENT,
            'less_than_equal': RoomErrorMessages.PRICE_EXCEEDED,
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
    daily_price: DailyPrice
    available: bool = True
    image: str = ''
    short_desc: RoomShortDesc
    long_desc: RoomLongDesc

    benefits: list[Benefit] = []
    room_class: RoomClass
    hotel: Hotel
    id: int | None = None


class Reservation(BaseEntity):
    """Represents a reservation.

    Attributes:
        checkin: date
        checkout: date
        client: Client
        room: Room
        observations: str
        amount: Decimal
        status: ReservationStatus
        created_at: date
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
    amount: Decimal
    status: ReservationStatus = ReservationStatusEnum.INITIALIZED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None

    @ensure_result
    def reservation_days(self) -> int:
        """Returns the reservation stayed period"""
        return (self.checkout - self.checkin).days

    @model_validator(mode='after')
    def validate_room(self):
        if not self.id and not self.room.available:
            raise ValueError(ReserveErrorMessages.UNAVAILABLE_ROOM)
        return self

    @model_validator(mode='after')
    def validate_dates(self):
        if self.id is None and self.checkin < date.today():
            raise ValueError(ReserveErrorMessages.INVALID_CHECKIN_DATE)

        if self.id is None and self.checkin > ReserveRules.checkin_anticipation_offset():
            raise ValueError(ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION)

        if self.checkin >= self.checkout:
            raise ValueError(ReserveErrorMessages.INVALID_CHECKIN_DATE)

        stayed_days = (self.checkout - self.checkin).days
        if not (
            ReserveRules.MIN_RESERVATION_DAYS
            <= stayed_days
            <= ReserveRules.MAX_RESERVATION_DAYS
        ):
            raise ValueError(ReserveErrorMessages.INVALID_STAYED_DAYS)

        return self
