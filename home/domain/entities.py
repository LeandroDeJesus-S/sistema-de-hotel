from base.entity import BaseEntity
from home.domain.value_objects import HotelName


class Hotel(BaseEntity):
    """Represents a hotel.

    Attributes:
        name: HotelName
        slogan: str
        presentation_text: str
        logo: str | None
        icon: str | None
    """

    name: HotelName
    slogan: str
    presentation_text: str
    logo: str | None = None
    icon: str | None = None

    def __str__(self) -> str:
        return self.name
