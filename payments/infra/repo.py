from exc import Result
from utils.support import entity_to_model, model_to_entity

from ..domain.entities import Payment
from ..domain.ports import AbsPaymentsRepository
from ..models import Payment as PaymentModel


class PaymentRepository(AbsPaymentsRepository):
    """
    Concrete implementation of the payment repository using Django ORM.
    """

    def __init__(self):
        self._model_cls = PaymentModel
        self._entity_cls = Payment

    def create(self, payment: Payment) -> Result[Payment]:
        """
        Creates a new payment record in the database.
        """
        try:
            payment_model_result = entity_to_model(payment, self._model_cls)
            if payment_model_result.is_err():
                return Result.Err(
                    'Failed to convert payment entity to model',
                    src_error=payment_model_result.unwrap_err(),
                )

            payment_model = payment_model_result.unwrap()
            payment_model.save()

            created_entity_result = model_to_entity(payment_model, self._entity_cls)
            if created_entity_result.is_err():
                return Result.Err(
                    'Failed to convert created payment model back to entity',
                    src_error=created_entity_result.unwrap_err(),
                )

            return Result.Ok(created_entity_result.unwrap())
        except Exception as e:
            return Result.Err('Failed to create payment in database', src_error=e)

    def get_by_reservation_id(self, reservation_id: int) -> Result[Payment]:
        """
        Gets a payment from the database by its reservation ID.
        """
        try:
            payment_model = self._model_cls.objects.filter(
                reservation__id=reservation_id
            ).first()
            if not payment_model:
                return Result.Err(msg='Payment not found for reservation', src_error=None)

            entity_result = model_to_entity(payment_model, self._entity_cls)
            if entity_result.is_err():
                return Result.Err(
                    'Failed to convert payment model to entity',
                    src_error=entity_result.unwrap_err(),
                )
            return Result.Ok(entity_result.unwrap())
        except Exception as e:
            return Result.Err(
                f'Failed to get payment for reservation {reservation_id}', src_error=e
            )

    def get_by_gateway_session_id(self, session_id: str) -> Result[Payment]:
        """
        Gets a payment from the database by its gateway session ID.
        """
        try:
            payment_model = self._model_cls.objects.filter(
                gateway_payment_session_id=session_id
            ).first()
            if not payment_model:
                return Result.Err(msg='Payment not found for session', src_error=None)

            entity_result = model_to_entity(payment_model, self._entity_cls)
            if entity_result.is_err():
                return Result.Err(
                    'Failed to convert payment model to entity',
                    src_error=entity_result.unwrap_err(),
                )
            return Result.Ok(entity_result.unwrap())
        except Exception as e:
            return Result.Err(
                f'Failed to get payment for session {session_id}',
                src_error=e,
            )

    def get_by_gateway_payment_intent_id(self, payment_intent_id: str) -> Result[Payment]:
        """
        Gets a payment from the database by its gateway payment intent ID.
        """
        try:
            payment_model = self._model_cls.objects.filter(
                gateway_payment_intent_id=payment_intent_id
            ).first()
            if not payment_model:
                return Result.Err(msg='Payment not found for payment intent', src_error=None)

            entity_result = model_to_entity(payment_model, self._entity_cls)
            if entity_result.is_err():
                return Result.Err(
                    'Failed to convert payment model to entity',
                    src_error=entity_result.unwrap_err(),
                )
            return Result.Ok(entity_result.unwrap())
        except Exception as e:
            return Result.Err(
                f'Failed to get payment for payment intent {payment_intent_id}',
                src_error=e,
            )

    def update(self, payment: Payment) -> Result[Payment]:
        """
        Updates an existing payment record in the database.
        """
        try:
            payment_model_result = entity_to_model(payment, self._model_cls)
            if payment_model_result.is_err():
                return Result.Err(
                    'Failed to convert payment entity to model for update',
                    src_error=payment_model_result.unwrap_err(),
                )

            payment_model = payment_model_result.unwrap()
            payment_model.save()

            updated_entity_result = model_to_entity(payment_model, self._entity_cls)
            if updated_entity_result.is_err():
                return Result.Err(
                    'Failed to convert updated payment model back to entity',
                    src_error=updated_entity_result.unwrap_err(),
                )
            return Result.Ok(updated_entity_result.unwrap())
        except Exception as e:
            return Result.Err(f'Failed to update payment {payment.id}', src_error=e)

    def get_by_id(self, payment_id: int) -> Result[Payment]:
        """returns a payment by its id"""
        if payment_model := self._model_cls.objects.filter(id=payment_id).first():
            return model_to_entity(payment_model, self._entity_cls)
        return Result.Err('Payment not found')
