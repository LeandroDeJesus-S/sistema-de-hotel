import logging

from dependency_injector.wiring import Provide
from django.conf import settings
from django.core.mail import send_mass_mail
from django.utils.timezone import now

from clients.models import Client
from payments.models import Payment
from reservations.container import ReservationsContainer
from reservations.models import Reservation, Room


# TODO move to reservations.infra.tasks properly
def check_reservation_dates(logger: logging.Logger = Provide[ReservationsContainer.logger]):
    """filtra por reservas ativas e verifica se a data de checkout é menor
    ou igual a data atual, caso seja, desativa a reserva e passa o status para
    finalizada, envia email avisando ao cliente e os admins
    """
    active_reservations = Reservation.objects.filter(status='A')
    for reservation in active_reservations:
        if reservation.checkout <= now().date():
            reservation.status = 'F'
            reservation.save()

            room = Room.objects.get(pk=reservation.room.pk)
            room.available = True
            room.save()

            logger.info(
                f'{reservation} encerrada. Quarto {reservation.room} '
                'liberado para novas reservas.'
            )
            message1 = (
                'Vencimento da reserva',
                'Olá, passando pra avisar que a sua reserva expirou!',
                settings.DEFAULT_FROM_EMAIL,
                [reservation.client.email],
            )

            admin_users = Client.objects.filter(is_staff=True)
            admin_emails = [adm.email for adm in admin_users if adm.email]
            message2 = (
                'Vencimento da reserva',
                f'Reserva de {reservation.client.complete_name} para o quarto '
                f'Nº{reservation.room.number} expirou!',
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
            )
            send_mass_mail((message1, message2), fail_silently=False)


def release_room(
    reservation_pk, logger: logging.Logger = Provide[ReservationsContainer.logger]
):
    """libera o quarto caso a reserva não tenha um pagamento finalizado"""
    try:
        reservation = Reservation.objects.get(pk=reservation_pk)
        payment = Payment.objects.filter(reservation=reservation).first()
        if payment is None or payment.status != Payment.Status.COMPLETED:
            logger.info(
                f'room {reservation.room} of the reservation {reservation_pk} released'
            )
            room = Room.objects.get(pk=reservation.room.pk)
            room.available = True
            room.save()
            print(f'quarto {room} da reserva {reservation} está disponível novamente.')

    except Reservation.DoesNotExist:
        pass
