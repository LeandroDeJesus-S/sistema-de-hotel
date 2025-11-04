from abc import ABC, abstractmethod
from typing import Protocol

from exc import Result
from payments.domain.dtos import CheckoutResultDTO, CheckoutSessionInputDTO

from .entities import Payment


class AbsSessionBasedPayment(Protocol):
    def create_checkout_session(
        self,
        dto: CheckoutSessionInputDTO,
    ) -> Result[CheckoutResultDTO]: ...


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
    def update(self, payment: Payment) -> Result[Payment]:
        """
        Updates an existing payment record.

        Args:
            payment: The payment entity to be updated.

        Returns:
            A Result containing the updated payment entity on success, or an Error on failure.
        """
        raise NotImplementedError
