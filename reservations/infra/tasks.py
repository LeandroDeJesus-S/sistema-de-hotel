import logging

from dependency_injector.wiring import Provide, inject
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as gtl

from base.ports.email import AbsEmailSender
from base.ports.queue import TaskQueuer
from exc import Result
from payments.domain.ports import AbsPaymentsRepository
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.container import ReservationsContainer
from reservations.domain.repo import AbsReservationRepository, AbsRoomRepository
from reservations.domain.value_objects import ReservationStatusEnum


@inject
def activate_reservation_task(
    reservation_id: int,
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    usecase: ActivateReservationUseCase = Provide[
        ReservationsContainer.activate_reservation_usecase
    ],
) -> Result[None]:
    """
    Activates a reservation by setting its status to ACTIVE and making the room unavailable.

    Args:
        reservation_id: The ID of the reservation to activate.
        reservation_repo: Optional. The reservation repository to use. Defaults to
            ReservationRepository.
        room_repo: Optional. The room repository to use. Defaults to RoomRepository.
        unit_of_work: Optional. The unit of work to use. Defaults to UNIT_OF_WORK.

    Returns:
        A Result indicating success or failure.
    """

    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise (Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err())

    reservation = reservation_result.unwrap()
    res = usecase(reservation)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)


@inject
def release_reservation_task(
    reservation_id: int,
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    usecase: ReleaseReservationUseCase = Provide[
        ReservationsContainer.release_reservation_usecase
    ],
) -> Result[None]:
    """
    Releases a reservation by setting its status to finished and making the room available.

    Args:
        reservation_id: The ID of the reservation to release.
        room_repo: Optional. The room repository to use. Defaults to RoomRepository.
        reservation_repo: Optional. The reservation repository to use. Defaults to
            ReservationRepository.
        payment_repo: Optional. The payment repository to use. Defaults to PaymentRepository.
        unit_of_work: Optional. The unit of work to use. Defaults to UnitOfWork.

    Returns:
        A Result indicating success or failure.
    """

    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise (Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err())

    reservation = reservation_result.unwrap()
    res = usecase(reservation)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)


@inject
def schedule_reservation_task(
    reservation_id: int,
    usecase: ScheduleReservationUseCase = Provide[
        ReservationsContainer.schedule_reservation_usecase
    ],
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
) -> Result[None]:
    """
    Schedules a reservation by setting its status to scheduled and making the reservation
    active.

    Args:
        reservation_id: The ID of the reservation to schedule.

    Returns:
        A Result indicating success or failure.
    """

    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise (Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err())

    reservation = reservation_result.unwrap()
    res = usecase(reservation)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)


@inject
def send_cancellation_notification(
    reservation_id: int,
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    task_queuer: TaskQueuer = Provide[ReservationsContainer.task_queuer],
) -> Result[None]:
    """
    Queue cancellation notification email tasks.

    Args:
        reservation_id: The ID of the cancelled reservation.

    Returns:
        A Result indicating success or failure.
    """
    # Validate reservation exists before queuing
    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise Result.Err(f'Reservation {reservation_id} not found').unwrap_err()

    task_queuer.queue_task(
        send_cancellation_client_email_task,
        (reservation_id,),
        name=f'send_cancellation_client_{reservation_id}',
    )
    task_queuer.queue_task(
        send_cancellation_admin_email_task,
        (reservation_id,),
        name=f'send_cancellation_admin_{reservation_id}',
    )
    return Result.Ok(None)


@inject
def send_scheduling_notification(
    reservation_id: int,
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    task_queuer: TaskQueuer = Provide[ReservationsContainer.task_queuer],
) -> Result[None]:
    """
    Queue scheduling notification email task.

    Args:
        reservation_id: The ID of the scheduled reservation.

    Returns:
        A Result indicating success or failure.
    """
    # Validate reservation exists before queuing
    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        raise Result.Err(f'Reservation {reservation_id} not found').unwrap_err()

    task_queuer.queue_task(
        send_scheduling_email_task, (reservation_id,), name=f'send_scheduling_{reservation_id}'
    )
    return Result.Ok(None)


@inject
def send_reservation_expired_client_email_task(
    reservation_id: int,
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    mailer: AbsEmailSender = Provide[ReservationsContainer.email_sender],
) -> None:
    """Send reservation expired notification email to client."""
    try:
        reservation_result = reservation_repo.find_by_id(reservation_id)
        if reservation_result.is_err():
            raise Result.Err(f'Reservation {reservation_id} not found').unwrap_err()

        reservation = reservation_result.unwrap()
        client_context = {'reservation': reservation, 'client': reservation.client}
        client_html_message = render_to_string(
            'emails/reservation_expired_client.html', client_context
        )
        mailer.send_single_mail(
            subject=gtl('Reservation Expired'),
            body=client_html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=[reservation.client.email],
            is_html=True,
        )
    except Exception as e:
        raise Result.Err(
            'Failed to send reservation expired client email', src_error=e
        ).unwrap_err()


@inject
def send_reservation_expired_admin_email_task(
    reservation_id: int,
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    mailer: AbsEmailSender = Provide[ReservationsContainer.email_sender],
) -> None:
    """Send reservation expired notification email to admins."""
    try:
        reservation_result = reservation_repo.find_by_id(reservation_id)
        if reservation_result.is_err():
            raise Result.Err(f'Reservation {reservation_id} not found').unwrap_err()

        reservation = reservation_result.unwrap()
        admin_context = {'reservation': reservation, 'client': reservation.client}
        admin_html_message = render_to_string(
            'emails/reservation_expired_admin.html', admin_context
        )
        mailer.send_single_mail(
            subject=gtl('Reservation Expired - %s') % reservation.id,
            body=admin_html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=list(settings.ADMINS),
            is_html=True,
        )
    except Exception as e:
        raise Result.Err(
            'Failed to send reservation expired admin email', src_error=e
        ).unwrap_err()


@inject
def send_cancellation_client_email_task(
    reservation_id: int,
    payments_repo: AbsPaymentsRepository = Provide[ReservationsContainer.payment_repo],
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    mailer: AbsEmailSender = Provide[ReservationsContainer.email_sender],
) -> None:
    """Send cancellation notification email to client."""
    try:
        # Get reservation details
        reservation_result = reservation_repo.find_by_id(reservation_id)
        if reservation_result.is_err():
            raise Result.Err(f'Reservation {reservation_id} not found').unwrap_err()

        reservation = reservation_result.unwrap()

        # Get payment details for refund information
        payment_result = payments_repo.get_by_reservation_id(reservation_id)
        refund_info = None
        if payment_result.is_ok():
            payment = payment_result.unwrap()
            if payment.refunded_amount:
                refund_info = {'amount': payment.refunded_amount, 'date': payment.refunded_at}

        # Send email to client
        client_subject = gtl('Reservation Cancellation Confirmation')
        client_context = {
            'reservation': reservation,
            'refund_info': refund_info,
            'client': reservation.client,
        }

        client_html_message = render_to_string(
            'emails/cancellation_notification_client.html', client_context
        )
        mailer.send_single_mail(
            subject=client_subject,
            body=client_html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=[reservation.client.email],
            is_html=True,
        )
    except Exception as e:
        raise Result.Err('Failed to send cancellation client email', src_error=e).unwrap_err()


@inject
def send_cancellation_admin_email_task(
    reservation_id: int,
    payments_repo: AbsPaymentsRepository = Provide[ReservationsContainer.payment_repo],
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    mailer: AbsEmailSender = Provide[ReservationsContainer.email_sender],
) -> None:
    """Send cancellation notification email to admins."""
    try:
        # Get reservation details
        reservation_result = reservation_repo.find_by_id(reservation_id)
        if reservation_result.is_err():
            raise Result.Err(f'Reservation {reservation_id} not found').unwrap_err()

        reservation = reservation_result.unwrap()

        # Get payment details for refund information
        payment_result = payments_repo.get_by_reservation_id(reservation_id)
        refund_info = None
        if payment_result.is_ok():
            payment = payment_result.unwrap()
            if payment.refunded_amount:
                refund_info = {'amount': payment.refunded_amount, 'date': payment.refunded_at}

        # Send email to admins
        admin_subject = gtl('Reservation Cancelled - %s') % reservation.id
        admin_context = {
            'reservation': reservation,
            'refund_info': refund_info,
            'client': reservation.client,
        }

        admin_html_message = render_to_string(
            'emails/cancellation_notification_admin.html', admin_context
        )
        mailer.send_single_mail(
            admin_subject,
            admin_html_message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email for admin_email in settings.ADMINS],
            is_html=True,
        )
    except Exception as e:
        raise Result.Err('Failed to send cancellation admin email', src_error=e).unwrap_err()


@inject
def send_scheduling_email_task(
    reservation_id: int,
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    mailer: AbsEmailSender = Provide[ReservationsContainer.email_sender],
) -> None:
    """Send scheduling notification email to client."""
    try:
        # Get reservation details
        reservation_result = reservation_repo.find_by_id(reservation_id)
        if reservation_result.is_err():
            raise Result.Err(f'Reservation {reservation_id} not found').unwrap_err()

        reservation = reservation_result.unwrap()

        # Send email to client
        client_subject = gtl('Reservation Scheduling Confirmation')
        client_context = {
            'reservation': reservation,
            'client': reservation.client,
        }

        client_html_message = render_to_string(
            'emails/scheduling_notification_client.html', client_context
        )
        mailer.send_single_mail(
            subject=client_subject,
            body=client_html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=[reservation.client.email],
        )
    except Exception as e:
        raise Result.Err('Failed to send scheduling email', src_error=e).unwrap_err()


@inject
def check_reservation_dates_task(
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    room_repo: AbsRoomRepository = Provide[ReservationsContainer.room_repo],
    task_queuer: TaskQueuer = Provide[ReservationsContainer.task_queuer],
    logger: logging.Logger = Provide[ReservationsContainer.logger],
) -> Result[None]:
    """
    Checks active reservations and finalizes those past their checkout date.

    Filters for active reservations and verifies if the checkout date is less than
    or equal to the current date. If so, sets the status to finished, makes the
    room available, logs the action, and sends HTML notification emails to the
    client and admins. Continues processing other reservations even if individual
    operations fail.

    Returns:
        A Result indicating success or failure.
    """
    try:
        active_reservations_result = reservation_repo.fetch_all_active()
        if active_reservations_result.is_err():
            raise Result.Err(
                'failed to fetch active reservations',
                src_error=active_reservations_result.unwrap_err(),
            ).unwrap_err()

        active_reservations = active_reservations_result.unwrap()

        failures = []
        for reservation in active_reservations:
            if reservation.checkout > now().date():
                continue

            # Update reservation status
            reservation.status = ReservationStatusEnum.FINISHED
            save_result = reservation_repo.save(reservation)
            if save_result.is_err():
                logger.error(
                    f'Failed to save reservation {reservation.id}: '
                    f'{save_result.unwrap_err().msg}'
                )
                failures.append(save_result.unwrap_err())
                continue

            # Update room availability
            if reservation.room.id is None:
                logger.error(f'Reservation {reservation.id} has room with no id')
                failures.append(Result.Err('Reservation has room with no id').unwrap_err())
                continue
            room_result = room_repo.find_by_id(reservation.room.id)
            if room_result.is_err():
                logger.error(
                    f'Failed to find room {reservation.room.id}: '
                    f'{room_result.unwrap_err().msg}'
                )
                failures.append(room_result.unwrap_err())
                continue

            room = room_result.unwrap()
            room.available = True
            room_save_result = room_repo.save(room)
            if room_save_result.is_err():
                logger.error(
                    f'Failed to save room {room.id}: {room_save_result.unwrap_err().msg}'
                )
                failures.append(room_save_result.unwrap_err())
                continue

            logger.info(f'{reservation} finalized. Room {reservation.room} made available.')

            # Queue email tasks
            task_queuer.queue_task(
                send_reservation_expired_client_email_task,
                (reservation.id,),
                name=f'send_reservation_expired_client_{reservation.id}',
            )
            task_queuer.queue_task(
                send_reservation_expired_admin_email_task,
                (reservation.id,),
                name=f'send_reservation_expired_admin_{reservation.id}',
            )

        if failures:
            logger.error(
                f'Failed to finalize some reservations: {len(failures)} errors occurred'
            )
        return Result.Ok(None)
    except Exception as e:
        raise (Result.Err('Failed to check reservation dates', src_error=e).unwrap_err())
