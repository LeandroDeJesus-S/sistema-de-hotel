from pydantic import FutureDatetime, JsonValue, PositiveInt

from base.entity import BaseEntity


class CheckoutResultDTO(BaseEntity):
    """Standardized response object for payment session creation.

    Attributes:
        client_id (str): The client ID on gateway.
        session_id (str): The checkout session ID.
        session_url (str): The checkout session URL.
    """

    client_id: str
    session_id: str
    session_url: str


class CheckoutItemDTO(BaseEntity):
    name: str
    description: str | None = None
    unit_price_cents: PositiveInt
    quantity: int = 1


class CheckoutSessionInputDTO(BaseEntity):
    expires_at: FutureDatetime
    success_url: str
    return_url: str
    items: list[CheckoutItemDTO]
    currency: str
    metadata: dict[str, JsonValue] | None = None
