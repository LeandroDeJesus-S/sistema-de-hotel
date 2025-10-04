from datetime import date

from pydantic import BaseModel


class CreateReservationInput(BaseModel):
    """DTO for creating a new reservation."""

    client_id: int
    room_pk: int
    check_in: date
    check_out: date
    observations: str
