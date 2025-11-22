from base.entity import BaseEntity
from clients.domain.entities import Client
from payments.domain.dtos import CheckoutSessionInputDTO
from reservations.domain.entities import Reservation


class CheckoutUseCaseInputDTO(BaseEntity):
    """Data Transfer Object for initiating a checkout."""

    client: Client
    reservation: Reservation
    checkout_session_input: CheckoutSessionInputDTO


# class CheckoutResultDTO(BaseModel):
#     """Data Transfer Object for the result of a checkout."""
#
#     client_id: str
#     checkout_session_id: str
#     redirect_url: str
