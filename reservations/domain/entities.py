from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import StringConstraints, model_validator

from base.entity import BaseEntity
from clients.domain.entities import Client
from home.domain.entities import Hotel
from reservations.domain.value_objects import (
    AdultsCapacity,
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

from .value_objects import RoomNumber


class Benefit(BaseEntity):
    """Represents a benefit from a room.

    Attributes:
        name: BenefitName
        icon: str
        short_desc: BenefitShortDesc
    """

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
    icon: Annotated[str, StringConstraints(min_length=1)]
    short_desc: BenefitShortDesc


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
    image: str
    short_desc: RoomShortDesc
    long_desc: RoomLongDesc

    benefits: list[Benefit]
    room_class: RoomClass
    hotel: Hotel


class Reservation(BaseEntity):
    """Represents a reservation.

    Attributes:
        checkin: date
        checkout: date
        client: Client
        room: Room
        observations: str
        amount: Decimal
        active: bool
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
    checkin: date
    checkout: date
    client: Client
    room: Room
    observations: ReservationObservations
    amount: Decimal
    status: ReservationStatus
    created_at: date

    @model_validator(mode='after')
    def validate_dates(self):
        if self.checkin < date.today():
            raise ValueError(ReserveErrorMessages.INVALID_CHECKIN_DATE)

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
