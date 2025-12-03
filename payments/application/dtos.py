from base.entity import BaseEntity


class CheckoutUseCaseInputDTO(BaseEntity):
    """Data Transfer Object for initiating a checkout.

    Attributes:
        client_id (int | None): The ID of the client initiating the checkout.
        reservation_id (int): The ID of the reservation for the checkout.
        success_url (str): The URL to redirect to on successful payment.
        cancel_url (str): The URL to redirect to if the payment is cancelled.
    """

    client_id: int | None = None
    reservation_id: int
    success_url: str
    cancel_url: str
