import logging
from datetime import datetime, timezone

from base.ports.unit_of_work import AbsUnitOfWork
from exc import Result

from ..domain.dtos import CheckoutResultDTO
from ..domain.entities import Payment, PaymentGateway, PaymentStatus
from ..domain.ports import AbsPaymentsRepository, AbsSessionBasedPayment
from .dtos import CheckoutUseCaseInputDTO


class CheckoutUseCase:
    """
    Use case for handling the checkout process.

    This use case orchestrates the creation of a payment session and a payment record.
    """

    def __init__(
        self,
        payment_repo: AbsPaymentsRepository,
        payment_gateway: AbsSessionBasedPayment,
        uow: AbsUnitOfWork,
        logger: logging.Logger,
    ):
        self._payment_repo = payment_repo
        self._payment_gateway = payment_gateway
        self._uow = uow
        self._logger = logger

    def __call__(self, dto: CheckoutUseCaseInputDTO) -> Result[CheckoutResultDTO]:
        """
        Executes the checkout use case.

        Args:
            dto: The data transfer object containing the checkout information.

        Returns:
            A Result containing the checkout result DTO on success, or an Error on failure.
        """

        with self._uow as w:
            session_result = self._payment_gateway.create_checkout_session(
                dto.checkout_session_input
            )
            if session_result.is_err():
                self._logger.error('Failed to create payment session')
                # w.rollback() WARN: be sure that there are no db operations in `create_checkout_session`  # noqa: E501
                return Result.Err(
                    'Failed to create payment session',
                    src_error=session_result.unwrap_err(),
                )

            checkout_result = session_result.unwrap()
            self._logger.debug(f'Payment session created: {checkout_result}')

            payment = Payment.safe_create(
                client=dto.client,
                reservation=dto.reservation,
                amount=dto.reservation.amount,
                status=PaymentStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                payment_gateway=PaymentGateway.STRIPE,
                gateway_customer_id=checkout_result.client_id,
                gateway_payment_intent_id=checkout_result.session_id,
                gateway_charge_id='',
            ).then(self._payment_repo.create)

            if payment.is_err():
                self._logger.error('Failed to create payment', exc_info=payment.unwrap_err())
                w.rollback()
                return Result.Err(
                    'Failed to create payment',
                    src_error=payment.unwrap_err(),
                )

        return session_result
