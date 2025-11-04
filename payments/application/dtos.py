from pydantic import BaseModel

from clients.domain.entities import Client
from payments.domain.dtos import CheckoutSessionInputDTO
from reservations.domain.entities import Reservation


class CheckoutUseCaseInputDTO(BaseModel):
    """Data Transfer Object for initiating a checkout."""

    client: Client
    reservation: Reservation
    checkout_session_input: CheckoutSessionInputDTO


class CheckoutResultDTO(BaseModel):
    """Data Transfer Object for the result of a checkout."""

    redirect_url: str
