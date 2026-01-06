from abc import ABC, abstractmethod
from typing import Any, Generic, Literal, Protocol, TypeVar

from exc import Result
from payments.domain.dtos import CheckoutResultDTO, CheckoutSessionInputDTO

from .entities import Payment


class AbsSessionBasedPayment(Protocol):
    @abstractmethod
    def create_checkout_session(
        self,
        dto: CheckoutSessionInputDTO,
    ) -> Result[CheckoutResultDTO]:
        """Creates a checkout session for a payment."""
        ...

    @abstractmethod
    def retrieve_checkout_session(self, session_id: str) -> Result[CheckoutResultDTO]:
        """Retrieves a checkout session from the gateway."""
        ...

    @abstractmethod
    def process_refund(
        self,
        payment_intent_id: str,
        amount: int,
        reason: Literal[
            'duplicate', 'fraudulent', 'requested_by_customer'
        ] = 'requested_by_customer',
    ) -> Result[dict]:
        """Process a refund of a payment through the gateway."""
        ...


class AbsPaymentsRepository(ABC):
    """Interface for a payment repository."""

    @abstractmethod
    def create(self, payment: Payment) -> Result[Payment]:
        """
        Creates a new payment record.

        Args:
            payment: The payment entity to be created.

        Returns:
            A Result containing the created payment entity on success, or an Error on failure.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_reservation_id(self, reservation_id: int) -> Result[Payment]:
        """
        Gets a payment by its reservation ID.

        Args:
            reservation_id: The ID of the reservation.

        Returns:
            A Result containing the payment entity or None if not found, or an Error on failure
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_gateway_session_id(self, session_id: str) -> Result[Payment]:
        """
        Gets a payment by its gateway session ID.

        Args:
            session_id: The session ID from the gateway.

        Returns:
            A Result containing the payment entity or None if not found, or an Error on failure
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_gateway_payment_intent_id(self, payment_intent_id: str) -> Result[Payment]:
        """
        Gets a payment by its gateway payment intent ID.

        Args:
            payment_intent_id: The payment intent ID from the gateway.

        Returns:
            A Result containing the payment entity or None if not found, or an Error on failure
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, payment: Payment) -> Result[Payment]:
        """
        Updates an existing payment record.

        Args:
            payment: The payment entity to be updated.

        Returns:
            A Result containing the updated payment entity on success, or an Error on failure.
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, payment_id: int) -> Result[Payment]:
        """
        Gets a payment by its ID.

        Args:
            payment_id: The ID of the payment.

        Returns:
            A Result containing the payment entity or None if not found, or an Error on failure
        """
        raise NotImplementedError

    @abstractmethod
    def get_pending_from(self, reservation_id: int) -> Result[Payment]:
        """Returns a pending payment from the database by its reservation ID if it exists."""


WebhookIdent = TypeVar('WebhookIdent')


class WebhookEvent(Protocol, Generic[WebhookIdent]):
    """Represents a webhook event sent by a payment gateway."""

    ident: WebhookIdent

    @abstractmethod
    def handle(self, data: dict[str, Any]) -> Result[None]:
        """performs the necessary actions to handle the webhook event."""
        ...


class PaymentWebhookHandler(Protocol, Generic[WebhookIdent]):
    """Class responsible for handling payment webhooks from payment gateways."""

    events: dict[WebhookIdent, WebhookEvent[WebhookIdent]]

    @abstractmethod
    def with_events(self, *event: WebhookEvent[WebhookIdent]) -> Result[None]:
        """Registers a list of events to be handled."""
        ...

    @abstractmethod
    def handle_webhook(self, data: dict[str, Any]) -> Result[None]:
        """Handles a webhook event dispatching by its identifier."""
        ...


class WebhookSignatureError(Exception):
    pass


class WebhookPayloadError(Exception):
    pass
