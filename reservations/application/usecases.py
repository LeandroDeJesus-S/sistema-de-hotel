import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Dict

from django.utils import timezone

from base.ports.queue import TaskQueuer
from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.domain.ports import AbsPaymentsRepository
from reservations import feedback_messages
from reservations.domain.entities import Reservation
from reservations.domain.value_objects import ReservationStatusEnum
from utils.support import get_available_dates_message

from ..domain.repo import AbsReservationRepository, AbsRoomRepository
from .dtos import CreateReservationInput


class InitializeReservationUseCase:
    def __init__(
        self,
        reservation_repo: AbsReservationRepository,
        room_repo: AbsRoomRepository,
        client_repo: AbsClientRepository,
        unit_of_work: AbsUnitOfWork,
        logger: logging.Logger,
    ):
        self.reservation_repo = reservation_repo
        self.room_repo = room_repo
        self.client_repo = client_repo
        self.unit_of_work = unit_of_work
        self.logger = logger

    def __call__(self, command: CreateReservationInput) -> Result[Reservation]:
        """Fetches the room, check if its available then checks for overlapping reservations
        and creates the reservation"""
        return (
            self._find_client(command)
            .then(self._find_room)
            .then(self._check_overlap)
            .then(self._create_reservation_entity)
            .then(self._save_reservation)
        )

    def _find_client(self, command: CreateReservationInput) -> Result[Dict]:
        client_result = self.client_repo.get_by_id(command.client_id)
        if client_result.is_err():
            return Result.Err(msg='client not found', src_error=client_result.unwrap_err())
        return Result.Ok({'command': command, 'client': client_result.unwrap()})

    def _find_room(self, data: Dict) -> Result[Dict]:
        command = data['command']
        room_result = self.room_repo.find_by_id(command.room_pk)
        if room_result.is_err() or not room_result.unwrap():
            return Result.Err(msg='room not found', src_error=room_result.unwrap_err())
        data['room'] = room_result.unwrap()
        return Result.Ok(data)

    def _check_overlap(self, data: Dict) -> Result[Dict]:
        command = data['command']
        overlap_result = self.reservation_repo.has_overlapping_reservation(
            room_id=command.room_pk,
            check_in=command.check_in,
            check_out=command.check_out,
        )
        if overlap_result.is_err() or overlap_result.unwrap():
            result = self.reservation_repo.from_room(command.room_pk).then(
                get_available_dates_message
            )
            if result.is_err():
                return Result.Err(msg='The room is not available')
            return Result.Err(msg=result.unwrap())
        return Result.Ok(data)

    def _create_reservation_entity(self, data: Dict) -> Result[Reservation]:  # noqa: PLR6301
        command = data['command']
        client = data['client']
        room = data['room']

        result = Reservation.safe_create(
            client=client,
            room=room,
            checkin=command.check_in,
            checkout=command.check_out,
            observations=command.observations,
            amount=Decimal(
                '0'
            ),  # bypass to be sure that checkin/checkout are valid validates at first
            status=ReservationStatusEnum.INITIALIZED,
        )
        if result.is_err():
            return Result.Err(
                msg=feedback_messages.ReservationMessages.RESERVATION_FAIL,
                src_error=result.unwrap_err(),
            )

        reservation = result.unwrap()
        stayed_days = Decimal(str((command.check_out - command.check_in).days))
        reservation.amount = room.daily_price * stayed_days
        return Result.Ok(reservation)

    def _save_reservation(self, reservation_entity: Reservation) -> Result[Reservation]:
        self.logger.info('Saving reservation')
        with self.unit_of_work as uow:
            saved_reservation_result = self.reservation_repo.save(reservation_entity)
            if saved_reservation_result.is_err() or not saved_reservation_result.unwrap():
                uow.rollback()
                return Result.Err(
                    msg='failed to save reservation',
                    src_error=saved_reservation_result.unwrap_err(),
                )

            uow.commit()
            return Result.Ok(saved_reservation_result.unwrap())


class FetchClientActiveReservations:
    def __init__(self, repository: AbsReservationRepository):
        self._repo = repository

    def __call__(self, client_id: int, include_scheduled: bool) -> Result[list]:
        return self._repo.fetch_active_reservations(client_id, include_scheduled)


class FetchClientReservationHistoryUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, client_id: int) -> Result[list[Reservation]]:
        return self._repo.fetch_client_history(client_id)


class FetchReservationDetailUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, reservation_id: int, client_id: int) -> Result[Reservation]:
        return self._repo.fetch_for_history_detail(client_id, reservation_id)


class ActivateReservationUseCase:
    """
    Use case to activate a reservation.

    This involves setting the reservation status to ACTIVE, marking it as active,
    and making the associated room unavailable.
    """

    def __init__(
        self,
        reservation_repo: AbsReservationRepository,
        room_repo: AbsRoomRepository,
        unit_of_work: AbsUnitOfWork,
        logger: logging.Logger,
    ) -> None:
        self._reservation_repo = reservation_repo
        self._room_repo = room_repo
        self._unit_of_work = unit_of_work
        self._logger = logger

    def __call__(self, reservation: Reservation) -> Result[Reservation]:
        """
        Activates the given reservation.

        Args:
            reservation (Reservation): The reservation entity to activate.

        Returns:
            Result[Reservation]: A Result containing the activated reservation
                                 or an Error if the activation fails.
        """
        with self._unit_of_work as uow:
            reservation.status = ReservationStatusEnum.ACTIVE
            reservation.room.available = False

            room_save_result = self._room_repo.save(reservation.room)
            if room_save_result.is_err():
                uow.rollback()
                self._logger.error(
                    'Failed to save room state for reservation %s: %s',
                    reservation.id,
                    room_save_result.unwrap_err(),
                )
                return Result.Err(
                    msg='Failed to save room state',
                    src_error=room_save_result.unwrap_err(),
                )

            reservation_save_result = self._reservation_repo.save(reservation)
            if reservation_save_result.is_err():
                uow.rollback()
                self._logger.error(
                    'Failed to save reservation %s: %s',
                    reservation.id,
                    reservation_save_result.unwrap_err(),
                )
                return Result.Err(
                    msg='Failed to save reservation',
                    src_error=reservation_save_result.unwrap_err(),
                )

            uow.commit()
            self._logger.info('Reservation %s activated successfully.', reservation.id)
            return Result.Ok(reservation_save_result.unwrap())


class ScheduleReservationUseCase:
    """
    Use case to schedule a reservation for future activation.

    This involves setting the reservation status to SCHEDULED and
    scheduling a background task to activate it at the check-in time.
    """

    def __init__(
        self,
        reservation_repo: AbsReservationRepository,
        unit_of_work: AbsUnitOfWork,
        task_queuer: TaskQueuer,
        logger: logging.Logger,
    ) -> None:
        self._reservation_repo = reservation_repo
        self._unit_of_work = unit_of_work
        self._task_queuer = task_queuer
        self._logger = logger

    def __call__(self, reservation: Reservation) -> Result[Reservation]:
        """
        Schedules the given reservation.

        Args:
            reservation (Reservation): The reservation entity to schedule.

        Returns:
            Result[Reservation]: A Result containing the scheduled reservation
                                 or an Error if the scheduling fails.
        """
        DELTA_MINS = 30  # avoid conflicts with release reservation task

        with self._unit_of_work as uow:
            reservation.status = ReservationStatusEnum.SCHEDULED

            reservation_save_result = self._reservation_repo.save(reservation)
            if reservation_save_result.is_err():
                uow.rollback()
                self._logger.error(
                    'Failed to save reservation %s for scheduling: %s',
                    reservation.id,
                    reservation_save_result.unwrap_err(),
                )
                return Result.Err(
                    msg='Failed to save reservation for scheduling',
                    src_error=reservation_save_result.unwrap_err(),
                )

            # Schedule the task to activate the reservation at check-in time
            activation_time = datetime.combine(
                reservation.checkin, time(0, DELTA_MINS), tzinfo=timezone.utc
            )
            task_name = f'activate_reservation_{reservation.id}'
            self._task_queuer.schedule_task(
                func_path='reservations.infra.tasks.activate_reservation_task',
                run_at=activation_time,
                args=(reservation.id,),
                name=task_name,
            )

            self._logger.info(
                'Reservation %s scheduled for activation at %s.',
                reservation.id,
                activation_time,
            )

            # Send scheduling notification
            self._task_queuer.queue_task(
                'reservations.infra.tasks.send_scheduling_notification',
                (reservation.id,),
                name=f'send_scheduling_notification_{reservation.id}',
            )

            uow.commit()
            return Result.Ok(reservation_save_result.unwrap())


class ReleaseReservationUseCase:
    def __init__(
        self,
        room_repo: AbsRoomRepository,
        reservations_repo: AbsReservationRepository,
        payments_repo: AbsPaymentsRepository,
        unit_of_work: AbsUnitOfWork,
        logger: logging.Logger,
    ) -> None:
        self._room_repo = room_repo
        self._reservation_repo = reservations_repo
        self._payment_repo = payments_repo
        self._unit_of_work = unit_of_work
        self._logger = logger

    def __call__(self, reservation: Reservation) -> Result[bool]:
        with self._unit_of_work as uow:
            reservation.status = ReservationStatusEnum.FINISHED
            reservation.room.available = True
            reservation_save_result = self._reservation_repo.save(reservation)
            if reservation_save_result.is_err():
                uow.rollback()
                self._logger.error(
                    'Failed to save reservation %s for releasing: %s',
                    reservation.id,
                    reservation_save_result.unwrap_err(),
                )
                return Result.Err(
                    msg='Failed to save reservation for releasing',
                    src_error=reservation_save_result.unwrap_err(),
                )

            room_save_result = self._room_repo.save(reservation.room)

            if room_save_result.is_err():
                uow.rollback()
                self._logger.error(
                    'Failed to save room state for reservation %s: %s',
                    reservation.id,
                    room_save_result.unwrap_err(),
                )
                return Result.Err(
                    msg='Failed to save room state',
                    src_error=room_save_result.unwrap_err(),
                )

            uow.commit()

        return Result.Ok(True)


class CancelReservationUseCase:
    """
    Use case to cancel a reservation.

    This involves validating ownership, checking cancellation policy,
    updating reservation status, and triggering refund logic.
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        reservation_repo: AbsReservationRepository,
        room_repo: AbsRoomRepository,
        payments_repo: AbsPaymentsRepository,
        unit_of_work: AbsUnitOfWork,
        task_queuer: TaskQueuer,
        logger: logging.Logger,
    ) -> None:
        self._reservation_repo = reservation_repo
        self._room_repo = room_repo
        self._payments_repo = payments_repo
        self._unit_of_work = unit_of_work
        self._task_queuer = task_queuer
        self._logger = logger

    def __call__(
        self, reservation_id: int, client_id: int, reason: str = ''
    ) -> Result[Reservation]:
        """
        Cancels the given reservation.

        Args:
            reservation_id: ID of the reservation to cancel
            client_id: ID of the client requesting cancellation
            reason: Optional reason for cancellation

        Returns:
            Result[Reservation]: A Result containing the cancelled reservation
                                or an Error if cancellation fails.
        """
        return (
            self._find_reservation(reservation_id)
            .then(self._validate_ownership(client_id))
            .then(self._validate_cancellation_policy)
            .then(self._cancel_reservation(reason))
            .then(self._trigger_refund)
            .then(self._send_notifications)
        )

    def _find_reservation(self, reservation_id: int) -> Result[Reservation]:
        """Find the reservation by ID."""
        result = self._reservation_repo.find_by_id(reservation_id)
        if result.is_err():
            return Result.Err(
                msg=feedback_messages.ReservationMessages.RESERVATION_NOT_FOUND,
                src_error=result.unwrap_err(),
            )
        return Result.Ok(result.unwrap())

    def _validate_ownership(self, client_id: int):
        """Return a function to validate reservation ownership."""

        def validator(reservation: Reservation) -> Result[Reservation]:
            if reservation.client.id != client_id:
                return Result.Err(
                    msg=feedback_messages.ReservationMessages.UNAUTHORIZED_CANCELLATION
                )
            return Result.Ok(reservation)

        return validator

    def _validate_cancellation_policy(self, reservation: Reservation) -> Result[Reservation]:
        """Validate that the reservation can be cancelled according to policy."""
        # Check if reservation is in a cancellable state
        if reservation.status not in {
            ReservationStatusEnum.ACTIVE,
            ReservationStatusEnum.SCHEDULED,
        }:
            return Result.Err(
                msg=feedback_messages.ReservationMessages.CANNOT_CANCEL_RESERVATION
            )

        # Check 24-hour cancellation policy
        now = timezone.now()
        checkin_datetime = datetime.combine(reservation.checkin, time.min, tzinfo=now.tzinfo)

        if checkin_datetime - now < timedelta(hours=24):
            return Result.Err(msg=feedback_messages.ReservationMessages.CANCELLATION_TOO_LATE)

        return Result.Ok(reservation)

    def _cancel_reservation(self, reason: str):
        """Return a function to cancel the reservation."""

        def cancel(reservation: Reservation) -> Result[Reservation]:
            with self._unit_of_work as uow:
                # If reservation was active, make room available again
                was_active = reservation.status == ReservationStatusEnum.ACTIVE
                if was_active:
                    reservation.room.available = True
                    room_save_result = self._room_repo.save(reservation.room)
                    if room_save_result.is_err():
                        uow.rollback()
                        self._logger.error(
                            'Failed to restore room availability for reservation %s: %s',
                            reservation.id,
                            room_save_result.unwrap_err(),
                        )
                        return Result.Err(
                            msg='Failed to restore room availability',
                            src_error=room_save_result.unwrap_err(),
                        )

                reservation.status = ReservationStatusEnum.CANCELLED
                reservation.cancelled_at = timezone.now()
                reservation.cancellation_reason = reason

                save_result = self._reservation_repo.save(reservation)
                if save_result.is_err():
                    uow.rollback()
                    self._logger.error(
                        'Failed to cancel reservation %s: %s',
                        reservation.id,
                        save_result.unwrap_err(),
                    )
                    return Result.Err(
                        msg='Failed to cancel reservation',
                        src_error=save_result.unwrap_err(),
                    )

                uow.commit()
                self._logger.info('Reservation %s cancelled successfully.', reservation.id)
                return Result.Ok(save_result.unwrap())

        return cancel

    def _trigger_refund(self, reservation: Reservation) -> Result[Reservation]:
        """Trigger refund process for the cancelled reservation."""
        # Find associated payment
        if not reservation.id:
            self._logger.warning('Reservation has no ID, cannot process refund')
            return Result.Ok(reservation)

        payment_result = self._payments_repo.get_by_reservation_id(reservation.id)
        if payment_result.is_err():
            self._logger.warning(
                'No payment found for reservation %s during cancellation', reservation.id
            )
            # Don't fail the cancellation if no payment exists
            return Result.Ok(reservation)

        payment = payment_result.unwrap()

        # Only process refund if payment was completed
        if payment.status == 'completed':
            # Calculate refund amount based on policy
            refund_amount = self._calculate_refund_amount(reservation, payment)

            # Queue refund processing task
            self._task_queuer.queue_task(
                'payments.infra.tasks.process_refund',
                (payment.id, refund_amount, 'requested_by_customer'),
                name=f'process_refund_{payment.id}',
            )

        return Result.Ok(reservation)

    def _calculate_refund_amount(self, reservation: Reservation, payment) -> int:
        """Calculate refund amount in cents based on cancellation policy."""
        now = timezone.now()
        checkin_datetime = datetime.combine(reservation.checkin, time.min, tzinfo=now.tzinfo)

        # Full refund if more than 24 hours before check-in
        if checkin_datetime - now >= timedelta(hours=24):
            return int(payment.amount * 100)  # Full refund in cents

        # Partial refund (50%) if within 24 hours
        return int(payment.amount * 100 * Decimal('0.5'))

    def _send_notifications(self, reservation: Reservation) -> Result[Reservation]:
        """Send cancellation notifications."""
        self._task_queuer.queue_task(
            'reservations.infra.tasks.send_cancellation_notification',
            (reservation.id,),
            name=f'send_cancellation_notification_{reservation.id}',
        )
        return Result.Ok(reservation)
