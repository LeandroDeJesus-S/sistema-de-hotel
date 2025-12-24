from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import Field

from base.entity import BaseEntity
from clients.domain.entities import Client
from reservations.domain.entities import Reservation


class PaymentStatus(str, Enum):
    """Enumerates the possible states of a payment transaction."""

    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    CANCELLED = 'cancelled'


class PaymentMethodType(str, Enum):
    """Enumerates the types of payment methods."""

    CREDIT_CARD = 'credit_card'
    BANK_TRANSFER = 'bank_transfer'
    PIX = 'pix'
    UNKNOWN = 'unknown'


class PaymentGateway(str, Enum):
    """Enumerates the supported payment gateways."""

    STRIPE = 'stripe'
    PAYPAL = 'paypal'
    UNKNOWN = 'unknown'


class Payment(BaseEntity):
    """
    Domain entity representing a single payment transaction.
    It tracks the status and key identifiers from an external payment gateway.
    """

    client: Client
    reservation: Reservation
    amount: Decimal = Field(..., max_digits=10, decimal_places=2)
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method_type: PaymentMethodType = PaymentMethodType.UNKNOWN

    # --- External Gateway Information ---
    payment_gateway: PaymentGateway = PaymentGateway.UNKNOWN
    gateway_customer_id: str | None = None
    gateway_payment_intent_id: str | None = None
    gateway_payment_session_id: str | None = None
    gateway_charge_id: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    refunded_amount: float | None = None
    refunded_at: datetime | None = None
    refund_reason: str = ''

    def is_completed(self) -> bool:
        """Checks if the payment was successfully completed."""
        return self.status == PaymentStatus.COMPLETED
