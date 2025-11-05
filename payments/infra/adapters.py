from typing import Any

import stripe

from exc import Result
from payments.domain.dtos import CheckoutResultDTO, CheckoutSessionInputDTO
from payments.domain.entities import PaymentStatus
from payments.domain.ports import (
    AbsPaymentsRepository,
    AbsSessionBasedPayment,
    PaymentWebhookHandler,
    WebhookEvent,
    WebhookIdent,
)
from reservations.domain.value_objects import ReservationStatusEnum


class StripeCheckoutSession(AbsSessionBasedPayment):
    """Creates a payment flow using Stripe's CheckoutSession"""

    def __init__(self, stripe_api_key: str):
        self._stripe_api_key = stripe_api_key

    def create_checkout_session(
        self, dto: CheckoutSessionInputDTO
    ) -> Result[CheckoutResultDTO]:
        """Creates and returns a Stripe checkout session"""

        if len(dto.items) <= 0:
            return Result.Err('No items provided')

        try:
            metadata = dto.metadata or {}
            params: dict[str, Any] = {
                'metadata': metadata,
                'customer_email': metadata.get('customer_email'),
                'mode': 'payment',
                'success_url': dto.success_url,
                'cancel_url': dto.return_url,
                'expires_at': int(dto.expires_at.timestamp()),
                'line_items': [
                    {
                        'price_data': {
                            'currency': dto.currency,
                            'product_data': {
                                'name': item.name,
                                'description': item.description,
                            },
                            'unit_amount': item.unit_price_cents,
                        },
                        'quantity': item.quantity,
                    }
                    for item in dto.items
                ],
            }

            session = stripe.checkout.Session.create(**params, api_key=self._stripe_api_key)
            if not isinstance(session.customer, stripe.Customer):
                return Result.Err('Failed to create Stripe customer')

            result = CheckoutResultDTO.safe_create(
                session_id=session.id,
                session_url=session.url or '',
                client_id=session.customer.id,
            )
            if result.is_err():
                return Result.Err(
                    'Failed to create Stripe session', src_error=result.unwrap_err()
                )
            return Result.Ok(result.unwrap())

        except Exception as e:
            return Result.Err('Failed to create Stripe session', src_error=e)


class StripePaymentWebhookHandler(PaymentWebhookHandler[WebhookIdent]):
    """Class responsible for handling payment webhooks from stripe."""

    def __init__(self) -> None:
        self.events: dict[WebhookIdent, WebhookEvent[WebhookIdent]] = {}

    def with_events(self, *events: WebhookEvent[WebhookIdent]) -> Result[None]:
        """Registers a list of events to be handled."""
        for event in events:
            self.events[event.ident] = event
        return Result.Ok(None)

    def handle_webhook(self, event_ident: WebhookIdent, data: dict[str, Any]) -> Result[None]:
        """Handles a webhook event dispatching by its identifier."""
        if event_ident not in self.events:
            return Result.Err(f'Event {event_ident} not found')

        event = self.events[event_ident]
        result = event.handle(data)

        if result.is_err():
            return Result.Err(
                'Failed to handle webhook event',
                src_error=result.unwrap_err(),
            )

        return Result.Ok(None)


class CheckoutSucceededEvent(WebhookEvent[str]):
    """Handles the logic when a checkout session is successfully completed."""

    ident = 'checkout.session.completed'

    def __init__(self, payments_repo: AbsPaymentsRepository):
        self._payments_repo = payments_repo

    def handle(self, data: dict[str, Any]) -> Result[None]:
        """
        Updates the payment and reservation status upon successful checkout.
        """
        payment_intent_id = data.get('payment_intent')
        if not payment_intent_id:
            return Result.Err('Payment intent ID not found in webhook data')

        payment_result = self._payments_repo.get_by_gateway_payment_intent_id(
            payment_intent_id
        )
        if payment_result.is_err():
            return Result.Err(
                'Failed to retrieve payment by payment intent ID',
                src_error=payment_result.unwrap_err(),
            )

        payment = payment_result.unwrap()
        payment.status = PaymentStatus.COMPLETED
        payment.gateway_charge_id = data.get('latest_charge')
        if payment.reservation:
            payment.reservation.status = ReservationStatusEnum.SCHEDULED

        update_result = self._payments_repo.update(payment)
        if update_result.is_err():
            return Result.Err(
                'Failed to update payment and reservation status',
                src_error=update_result.unwrap_err(),
            )

        return Result.Ok(None)


class CheckoutExpiredEvent(WebhookEvent[str]):
    """Handles the event when a client cancels a payment."""

    ident = 'checkout.session.expired'

    def __init__(self, payments_repo: AbsPaymentsRepository):
        self._payments_repo = payments_repo

    def handle(self, data: dict[str, Any]) -> Result[None]:
        """
        Updates the payment and reservation status to cancelled.
        """
        payment_intent_id = data.get('payment_intent')
        if not payment_intent_id:
            return Result.Err('Payment intent ID not found in webhook data')

        payment_result = self._payments_repo.get_by_gateway_payment_intent_id(
            payment_intent_id
        )
        if payment_result.is_err():
            return Result.Err(
                'Failed to retrieve payment by payment intent ID',
                src_error=payment_result.unwrap_err(),
            )

        payment = payment_result.unwrap()
        payment.status = PaymentStatus.FAILED
        if payment.reservation:
            payment.reservation.status = ReservationStatusEnum.CANCELLED

        update_result = self._payments_repo.update(payment)
        if update_result.is_err():
            return Result.Err(
                'Failed to update payment and reservation to cancelled',
                src_error=update_result.unwrap_err(),
            )

        return Result.Ok(None)


class PaymentRefundEvent(WebhookEvent[str]):
    """Handles the event when a user refunds a payment."""

    ident = 'charge.refunded'

    def __init__(self, payments_repo: AbsPaymentsRepository):
        self._payments_repo = payments_repo

    def handle(self, data: dict[str, Any]) -> Result[None]:
        """
        Updates the payment status to refunded.
        """
        payment_intent_id = data.get('payment_intent')
        if not payment_intent_id:
            return Result.Err('Payment intent ID not found in webhook data')

        payment_result = self._payments_repo.get_by_gateway_payment_intent_id(
            payment_intent_id
        )
        if payment_result.is_err():
            return Result.Err(
                'Failed to retrieve payment by payment intent ID',
                src_error=payment_result.unwrap_err(),
            )

        payment = payment_result.unwrap()
        payment.status = PaymentStatus.REFUNDED

        update_result = self._payments_repo.update(payment)
        if update_result.is_err():
            return Result.Err(
                'Failed to update payment to refunded',
                src_error=update_result.unwrap_err(),
            )

        return Result.Ok(None)
