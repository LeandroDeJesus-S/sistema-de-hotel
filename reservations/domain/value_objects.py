from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import AwareDatetime, BeforeValidator, Field, StringConstraints

from utils.decorators import ensure_result

from .. import rules


class Currency(str, Enum):
    """Centralized currency definitions."""

    USD = 'usd'
    BRL = 'brl'


RoomNumber = Annotated[
    str,
    StringConstraints(
        pattern=rules.RoomRules.NUMBER_FORMAT,
        min_length=rules.RoomRules.NUMBER_MIN_LEN,
        max_length=rules.RoomRules.NUMBER_MAX_LEN,
    ),
    'Represents a room number value object that must be in the format 000[X].',
]

RoomClassName = Annotated[
    str,
    StringConstraints(
        min_length=rules.RoomClassRules.MIN_LEN,
        max_length=rules.RoomClassRules.MAX_LEN,
        pattern=rules.RoomClassRules.PATTERN,
    ),
    'Represents a room class value object.',
]

BenefitName = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=rules.BenefitRules.NAME_MAX_LEN,
        pattern=rules.BenefitRules.NAME_PATTERN,
    ),
    'Represents a benefit name value object.',
]

BenefitShortDesc = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=rules.BenefitRules.SHORT_DESC_MAX_LEN,
    ),
    'Represents a benefit short description value object.',
]

BenefitIcon = Annotated[
    str,
    StringConstraints(
        max_length=rules.BenefitRules.ICON_MAX_LEN,
    ),
    'Represents a benefit icon value object.',
]


class ReservationStatusEnum(str, Enum):
    INITIALIZED = 'I'
    PROCESSING = 'P'
    ACTIVE = 'A'
    CANCELLED = 'C'
    FINISHED = 'F'
    SCHEDULED = 'S'


ReservationStatus = ReservationStatusEnum

AdultsCapacity = Annotated[
    int,
    Field(ge=rules.RoomRules.MIN_ADULTS, le=rules.RoomRules.MAX_ADULTS),
    'represents the number of adults supported for a room',
]
ChildrenCapacity = Annotated[
    int,
    Field(ge=rules.RoomRules.MIN_CHILDREN, le=rules.RoomRules.MAX_CHILDREN),
    'represents the number of children supported for a room',
]
RoomSize = Annotated[
    float,
    Field(ge=rules.RoomRules.MIN_SIZE, le=rules.RoomRules.MAX_SIZE),
    'the dimension of a room in meters',
]
DailyPrice = Annotated[
    Decimal,
    Field(ge=rules.RoomRules.MIN_DAILY_PRICE, le=rules.RoomRules.MAX_DAILY_PRICE),
    'the price of a room per day',
]
RoomShortDesc = Annotated[
    str,
    Field(max_length=rules.RoomRules.SHORT_DESC_MAX_LEN),
    'a short description of a room',
]
RoomLongDesc = Annotated[
    str,
    Field(max_length=rules.RoomRules.LONG_DESC_MAX_LEN),
    'a detailed description of a room',
]
ReservationObservations = Annotated[
    str,
    Field(
        max_length=rules.ReserveRules.OBSERVATIONS_MAX_LEN,
        pattern=rules.ReserveRules.OBSERVATIONS_PATTERN,
    ),
    'represents observations made by the customer during the reservation',
]


PriceValue = Annotated[
    int,
    Field(ge=0),
    'price value in cents',
]


def cast_aware_datetime(d: date | datetime | str) -> datetime:
    if isinstance(d, str):
        conv_d = convert_datetime(d)
        if conv_d.is_err():
            raise ValueError(conv_d.unwrap_err().msg)
        return conv_d.unwrap()  # type: ignore
    elif isinstance(d, date) and not isinstance(d, datetime):
        # Convert date to datetime at midnight UTC
        return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
    elif isinstance(d, datetime):
        if d.tzinfo is None:
            raise ValueError('Datetime must be timezone-aware')
        return d
    else:
        raise ValueError(f'Cannot convert {type(d)} to timezone-aware datetime')


CheckInOut = Annotated[
    AwareDatetime,
    BeforeValidator(cast_aware_datetime),
    'represents a timezone-aware check-in/out datetime',
]


@ensure_result
def convert_datetime(value: str) -> datetime:
    """Converts a datetime string to `datetime.datetime`. Supports both date and
    datetime formats.

    Args:
        value (str): Date/datetime as a string.

    Returns:
        datetime.datetime: `datetime.datetime` instance of the formatted date/datetime.
    """
    try:
        # Try parsing as datetime first
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        # Ensure the result is timezone-aware
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        # Fall back to date parsing and convert to datetime
        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
        return datetime.combine(date_obj, datetime.min.time(), tzinfo=timezone.utc)
