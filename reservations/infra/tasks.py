from dependency_injector.wiring import Provide, inject
from django.conf import settings
from django.template.loader import render_to_string

from base.ports.email import AbsEmailSender
from exc import Result
from payments.domain.ports import AbsPaymentsRepository
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.container import ReservationsContainer
from reservations.domain.repo import AbsReservationRepository


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
        raise Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err()

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
        raise Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err()

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
        raise Result.Err(f'Reservation with id {reservation_id} not found.').unwrap_err()

    reservation = reservation_result.unwrap()
    res = usecase(reservation)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)


@inject
def send_cancellation_notification(
    reservation_id: int,
    payments_repo: AbsPaymentsRepository = Provide[ReservationsContainer.payment_repo],
    reservation_repo: AbsReservationRepository = Provide[
        ReservationsContainer.reservation_repo
    ],
    mailer: AbsEmailSender = Provide[ReservationsContainer.email_sender],
) -> Result[None]:
    """
    Send cancellation notification emails to client and admins.

    Args:
        reservation_id: The ID of the cancelled reservation.

    Returns:
        A Result indicating success or failure.
    """

    # Get reservation details
    reservation_result = reservation_repo.find_by_id(reservation_id)
    if reservation_result.is_err():
        return Result.Err(f'Reservation {reservation_id} not found')

    reservation = reservation_result.unwrap()

    # Get payment details for refund information
    payment_result = payments_repo.get_by_reservation_id(reservation_id)
    refund_info = None
    if payment_result.is_ok():
        payment = payment_result.unwrap()
        if payment.refunded_amount:
            refund_info = {'amount': payment.refunded_amount, 'date': payment.refunded_at}

    # Send email to client
    client_subject = 'Confirmação de Cancelamento de Reserva'
    client_context = {
        'reservation': reservation,
        'refund_info': refund_info,
        'client': reservation.client,
    }

    client_html_message = render_to_string(
        'emails/cancellation_notification_client.html', client_context
    )
    try:
        mailer.send_single_mail(
            subject=client_subject,
            body=client_html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=[reservation.client.email],
        )
    except Exception as e:
        return Result.Err('Failed to send client notification email', src_error=e)

    # Send email to admins
    admin_subject = f'Reserva Cancelada - {reservation.id}'
    admin_context = {
        'reservation': reservation,
        'refund_info': refund_info,
        'client': reservation.client,
    }

    admin_html_message = render_to_string(
        'emails/cancellation_notification_admin.html', admin_context
    )
    try:
        mailer.send_single_mail(
            admin_subject,
            admin_html_message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email for admin_email in settings.ADMINS],
        )
    except Exception as e:
        return Result.Err('Failed to send admin notification email', src_error=e)

    return Result.Ok(None)
