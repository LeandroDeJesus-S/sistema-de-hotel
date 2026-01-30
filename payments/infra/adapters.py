import json
import logging
from typing import Any, Callable, Literal

import stripe
from django.conf import settings

from base.ports.queue import TaskQueuer
from base.ports.unit_of_work import AbsUnitOfWork
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

    def __init__(self, stripe_api_key: str, logger: logging.Logger):
        self._stripe_api_key = stripe_api_key
        self._logger = logger

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
                pi_id=session.payment_intent or '',
            )
            if result.is_err():
                return Result.Err(
                    'Failed to create Stripe session', src_error=result.unwrap_err()
                )

            self._logger.debug(f'payment session successfully created: {session}')
            return Result.Ok(result.unwrap())

        except Exception as e:
            return Result.Err('Failed to create Stripe session', src_error=e)

    def retrieve_checkout_session(self, session_id: str) -> Result[CheckoutResultDTO]:
        """Retrieves a Stripe checkout session"""
        try:
            cs = stripe.checkout.Session.retrieve(session_id, api_key=self._stripe_api_key)
        except stripe.StripeError as e:
            return Result.Err('Failed to retrieve payment session', src_error=e)

        return CheckoutResultDTO.safe_create(
            session_id=cs.id,
            session_url=cs.url or '',
            client_id=cs.customer or '',
        )

    def process_refund(
        self,
        payment_intent_id: str,
        amount: int,
        reason: Literal[
            'duplicate', 'fraudulent', 'requested_by_customer'
        ] = 'requested_by_customer',
    ) -> Result[dict]:
        """Process a refund through Stripe."""
        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount,
                reason=reason,
                api_key=self._stripe_api_key,
            )
            return Result.Ok({
                'refund_id': refund.id,
                'amount': refund.amount,
                'status': refund.status,
            })
        except stripe.StripeError as e:
            return Result.Err('Failed to process refund', src_error=e)


class WebhookSignatureError(Exception):
    pass


class WebhookPayloadError(Exception):
    pass


class StripePaymentWebhookHandler(PaymentWebhookHandler[str]):
    """Class responsible for handling payment webhooks from stripe."""

    def __init__(self, logger: logging.Logger) -> None:
        self.events: dict[str, WebhookEvent[str]] = {}
        self.logger = logger

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
        send_confirmation_task: Callable[..., Any],
        activate_reservation_usecase: ActivateReservationUseCase,
        release_reservation_task: Callable[[int], Any],
        schedule_reservation_usecase: ScheduleReservationUseCase,
        unit_of_work: AbsUnitOfWork,
        logger: logging.Logger,
    ):
        self._task_queue = task_queue
        self._payments_repo = payments_repo
        self._send_confirmation_task = send_confirmation_task
        self._activate_reservation_usecase = activate_reservation_usecase
        self._release_reservation_task = release_reservation_task
        self._schedule_reservation_usecase = schedule_reservation_usecase
        self._unit_of_work = unit_of_work

        self._logger = logger

    def handle(self, data: dict[str, Any]) -> Result[None]:  # noqa: PLR0911
        """
        Updates the payment and reservation status upon successful checkout.
        It expects receive a stipre Charge object from the gateway.
        """
        self._logger.debug(f'[{self.ident}] {data}')

        payment_id = data.get('metadata', {}).get('internal_payment_id')
        pi_id = data.get('payment_intent', '')

        try:
            pi = stripe.PaymentIntent.retrieve(pi_id, api_key=settings.STRIPE_API_KEY_SECRET)
        except stripe.StripeError as e:
            return Result.Err('Failed to retrieve payment intent', src_error=e)

        if not pi.latest_charge:
            return Result.Err('Payment intent has no charge')

        with self._unit_of_work as uow:
            payment_result = self._payments_repo.get_by_id(payment_id)
            if payment_result.is_err():
                return Result.Err(
                    'Failed to retrieve payment by payment',
                    src_error=payment_result.unwrap_err(),
                )

            payment = payment_result.unwrap()
            payment.status = PaymentStatus.COMPLETED
            payment.gateway_charge_id = str(pi.latest_charge)
            payment.gateway_payment_intent_id = pi.id
            payment.gateway_customer_id = str(pi.customer)
            if (err := self._payments_repo.update(payment)) and err.is_err():
                uow.rollback()
                return Result.Err(
                    'Failed to update payment',
                    src_error=err.unwrap_err(),
                )

            run_at = payment.reservation.checkout
            # XXX: It might make sense send the the confirmation email even though something went wrong on schedule  # noqa: E501
            if payment.reservation.room.available:
                self._logger.info(f'Reservation {payment.reservation.id} activation started')
                res = self._activate_reservation_usecase(payment.reservation)
                if res.is_err():
                    self._logger.error(
                        f'Failed to activate reservation {payment.reservation.id}'
                    )
                    uow.rollback()
                    # return Result.Err('Failed to activate reservation', src_error=res.unwrap_err())  # noqa: E501

                self._task_queue.queue_task(
                    'payments.infra.tasks.send_payment_confirmation',
                    (payment.id,),
                    name=f'send_payment_confirmation_{payment.id}',
                )
                self._logger.info(f'payment confirmation scheduled for {payment.id}')
                self._task_queue.schedule_task(
                    func_path='reservations.infra.tasks.release_reservation_task',
                    run_at=run_at,
                    args=(payment.reservation.id,),
                    name=f'release_reservation_{payment.reservation.id}',
                )
                self._logger.info(
                    f'reservation release scheduled for {payment.reservation.id} at {run_at}'
                )
                uow.commit()
                return Result.Ok(None)

            self._logger.info(f'Reservation {payment.reservation.id} scheduling started')
            schedule_result = self._schedule_reservation_usecase(payment.reservation)
            if schedule_result.is_err():
                self._logger.error(
                    f'Failed to schedule reservation {payment.reservation.id}',
                    exc_info=schedule_result.unwrap_err(),
                )
                uow.rollback()
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
            self._logger.info(f'payment confirmation scheduled for {payment.id}')
            self._task_queue.schedule_task(
                func_path='reservations.infra.tasks.release_reservation_task',
                run_at=run_at,
                args=(payment.reservation.id,),
                name=f'release_reservation_{payment.reservation.id}',
            )
            self._logger.info(
                f'reservation release scheduled for {payment.reservation.id} at {run_at}'
            )
            uow.commit()
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
