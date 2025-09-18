from typing import Annotated

from pydantic import StringConstraints

from .. import rules

HotelName = Annotated[
    str,
    StringConstraints(
        max_length=rules.HotelRules.NAME_MAX_LEN,
    ),
    'Represents a hotel name value object.',
]
