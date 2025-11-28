from base.entity import BaseEntity
from clients.domain.entities import Client
from payments.domain.dtos import CheckoutSessionInputDTO
from payments.domain.entities import Payment
from reservations.domain.entities import Reservation


class CheckoutUseCaseInputDTO(BaseEntity):
    """Data Transfer Object for initiating a checkout.

    Attributes:
        client (Client | None): The client entity.
        reservation (Reservation | None): The reservation entity.
        checkout_session_input (CheckoutSessionInputDTO | None): The checkout session input DTO.
        pending_payment (Payment | None): The pending payment entity.
    """  # noqa: E501

    client: Client | None = None
    reservation: Reservation | None = None
    checkout_session_input: CheckoutSessionInputDTO | None = None
    pending_payment: Payment | None = None


# class CheckoutResultDTO(BaseModel):
#     """Data Transfer Object for the result of a checkout."""
#
#     client_id: str
#     checkout_session_id: str
#     redirect_url: str
