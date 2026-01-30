from base.entity import BaseEntity
from reservations.domain.value_objects import CheckInOut, Currency


class CreateReservationInput(BaseEntity):
    """DTO for creating a new reservation."""

    client_id: int
    room_pk: int
    check_in: CheckInOut
    check_out: CheckInOut
    observations: str
    currency: Currency | None = None
