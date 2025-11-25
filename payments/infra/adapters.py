import json
import logging
from datetime import datetime, time
from typing import Any, Callable

import stripe
from django.conf import settings

from base.ports.queue import TaskQueuer
from exc import Result
from payments.domain.dtos import CheckoutResultDTO, CheckoutSessionInputDTO
from payments.domain.entities import PaymentStatus
from payments.domain.ports import (
    AbsPaymentsRepository,
    AbsSessionBasedPayment,
    PaymentWebhookHandler,
    WebhookEvent,
)
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.domain.repo import AbsReservationRepository
from reservations.domain.value_objects import ReservationStatusEnum


class StripeCheckoutSession(AbsSessionBasedPayment):
    """Creates a payment flow using Stripe's CheckoutSession"""

    def __init__(self, stripe_api_key: str):
        self._stripe_api_key = stripe_api_key
        self._logger = logging.getLogger('djangoLogger')

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
            result = CheckoutResultDTO.safe_create(
                session_id=session.id,
                session_url=session.url or '',
                client_id=session.customer or '',
            )
            if result.is_err():
                return Result.Err(
                    'Failed to create Stripe session', src_error=result.unwrap_err()
                )

            self._logger.debug(f'payment session successfully created: {session}')
            return Result.Ok(result.unwrap())

        except Exception as e:
            return Result.Err('Failed to create Stripe session', src_error=e)


class WebhookSignatureError(Exception):
    pass


class WebhookPayloadError(Exception):
    pass


class StripePaymentWebhookHandler(PaymentWebhookHandler[str]):
    """Class responsible for handling payment webhooks from stripe."""

    def __init__(self) -> None:
        self.events: dict[str, WebhookEvent[str]] = {}
        self.logger = logging.getLogger('djangoLogger')

    def with_events(self, *events: WebhookEvent[str]) -> Result[None]:
        """Registers a list of events to be handled."""
        for event in events:
            self.events[event.ident] = event
        return Result.Ok(None)

    def handle_webhook(self, data: dict[str, Any]) -> Result[None]:
        """Handles a webhook event dispatching by its identifier."""
        payload = data.get('request_body', {})
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

        try:
            stripe_event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except ValueError as e:
            return Result.Err('invalid payload', src_error=WebhookPayloadError(str(e)))

        if endpoint_secret:
            sig_header = data.get('stripe_signature_header', '')
            try:
                stripe_event = stripe.Webhook.construct_event(
                    payload, sig_header, endpoint_secret
                )
            except stripe.SignatureVerificationError as e:
                self.logger.warning('Webhook signature verification failed.', exc_info=e)
                return Result.Err('invalid signature', src_error=WebhookSignatureError(str(e)))

        event = self.events.get(str(stripe_event.type))
        if not event:
            return Result.Ok(None)

        result = event.handle(stripe_event.data.object)

        if result.is_err():
            self.logger.error(
                'Failed to handle webhook event',
                exc_info=result.unwrap_err(),
            )
            return Result.Err(
                'Failed to handle webhook event',
                src_error=result.unwrap_err(),
            )

        return Result.Ok(None)


class CheckoutSucceededEvent(WebhookEvent[str]):
    """Handles the logic when a checkout session is successfully completed."""

    ident = 'checkout.session.completed'

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        task_queue: TaskQueuer,
        payments_repo: AbsPaymentsRepository,
        send_configuration_task: Callable[..., Any],
        activate_reservation_usecase: ActivateReservationUseCase,
        release_reservation_task: Callable[[int], Any],
        schedule_reservation_usecase: ScheduleReservationUseCase,
    ):
        self._task_queue = task_queue
        self._payments_repo = payments_repo
        self._send_confirmation_task = send_configuration_task
        self._activate_reservation_usecase = activate_reservation_usecase
        self._release_reservation_task = release_reservation_task
        self._schedule_reservation_usecase = schedule_reservation_usecase

        self._logger = logging.getLogger('djangoLogger')

    def handle(self, data: dict[str, Any]) -> Result[None]:  # noqa: PLR0911
        """
        Updates the payment and reservation status upon successful checkout.
        It expects receive a stipre Charge object from the gateway.
        """
        self._logger.debug(f'[{self.ident}] {data}')

        payment_id = data.get('metadata', {}).get('internal_payment_id')
        payment_intent_id = data.get('payment_intent')

        if not (payment_id and payment_intent_id):
            return Result.Err('Missing payment or payment intent ID')

        try:
            pi = stripe.PaymentIntent.retrieve(
                payment_intent_id, api_key=settings.STRIPE_API_KEY_SECRET
            )
        except stripe.StripeError as e:
            return Result.Err('Failed to retrieve payment intent', src_error=e)

        if not pi.latest_charge:
            return Result.Err('Payment intent has no charge')

        payment_result = self._payments_repo.get_by_id(payment_id)
        if payment_result.is_err():
            return Result.Err(
                'Failed to retrieve payment by payment', src_error=payment_result.unwrap_err()
            )

        payment = payment_result.unwrap()
        payment.status = PaymentStatus.COMPLETED
        payment.gateway_charge_id = str(pi.latest_charge)
        payment.gateway_payment_intent_id = payment_intent_id
        payment.gateway_customer_id = str(pi.customer)
        self._payments_repo.update(payment)

        run_at = datetime.combine(payment.reservation.checkout, time(0, 0))
        # XXX: It might make sense send the the confirmation email even though something went wrong on schedule  # noqa: E501
        if payment.reservation.room.available:
            self._logger.info(f'Reservation {payment.reservation.id} activation started')
            res = self._activate_reservation_usecase(payment.reservation)
            if res.is_err():
                self._logger.error(f'Failed to activate reservation {payment.reservation.id}')
                # return Result.Err('Failed to activate reservation', src_error=res.unwrap_err())  # noqa: E501

            self._task_queue.queue_task(
                'payments.infra.tasks.send_payment_confirmation',
                (payment.id,),
                name=f'send_payment_confirmation_{payment.id}',
            )
            self._task_queue.schedule_task(
                func_path='reservations.infra.tasks.release_reservation_task',
                run_at=run_at,
                args=(payment.reservation.id,),
                name=f'release_reservation_{payment.reservation.id}',
            )
            return Result.Ok(None)

        self._logger.info(f'Reservation {payment.reservation.id} scheduling started')
        schedule_result = self._schedule_reservation_usecase(payment.reservation)
        if schedule_result.is_err():
            self._logger.error(
                f'Failed to schedule reservation {payment.reservation.id}',
                exc_info=schedule_result.unwrap_err(),
            )
            #
            # return Result.Err(
            #     'Failed to schedule reservation',
            #     src_error=schedule_result.unwrap_err(),
            # )
        self._task_queue.queue_task(
            self._send_confirmation_task,
            (payment.id,),
            name=f'send_payment_confirmation_{payment.id}',
        )
        self._task_queue.schedule_task(
            func_path='reservations.infra.tasks.release_reservation_task',
            run_at=run_at,
            args=(payment.reservation.id,),
            name=f'release_reservation_{payment.reservation.id}',
        )
        return Result.Ok(None)


class CheckoutExpiredEvent(WebhookEvent[str]):
    """Handles the event when a client cancels a payment."""

    ident = 'checkout.session.expired'

    def __init__(
        self, payments_repo: AbsPaymentsRepository, reservation_repo: AbsReservationRepository
    ):
        self._payments_repo = payments_repo
        self._reservation_repo = reservation_repo

    def handle(self, data: dict[str, Any]) -> Result[None]:
        """
        Updates the payment and reservation status to cancelled.
        """
        payment_id = data.get('metadata', {}).get('internal_payment_id')
        if not payment_id:
            return Result.Err('Payment intent ID not found in webhook data')

        payment_result = self._payments_repo.get_by_id(payment_id)
        if payment_result.is_err():
            return Result.Err(
                'Failed to retrieve payment by payment intent ID',
                src_error=payment_result.unwrap_err(),
            )

        payment = payment_result.unwrap()
        payment.status = PaymentStatus.CANCELLED
        if payment.reservation:
            payment.reservation.status = ReservationStatusEnum.CANCELLED
            self._reservation_repo.save(payment.reservation)

        update_result = self._payments_repo.update(payment)
        if update_result.is_err():
            return Result.Err(
                'Failed to update payment and reservation to cancelled',
                src_error=update_result.unwrap_err(),
            )

        return Result.Ok(None)


class PaymentChargeRefundedEvent(WebhookEvent[str]):
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


class CheckoutSessionCreatedEvent(WebhookEvent[str]):
    """Handles the event when a checkout session is created."""

    ident = 'checkout.session.created'

    def __init__(self) -> None:
        pass

    def handle(self, data: dict[str, Any]) -> Result[None]:  # noqa: PLR6301
        print('checkout session created')
        print(data)
        return Result.Ok(None)
