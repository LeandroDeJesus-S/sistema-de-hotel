from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import Field, StringConstraints

from .. import rules

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
