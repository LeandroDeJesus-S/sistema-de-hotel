from django.core.mail import send_mass_mail
from django.conf import settings
from clients.models import Client
from reservations.models import Reservation, Room


def schedule_reservation(reservation_id):
    reservation = Reservation.objects.get(pk=int(reservation_id))
    reservation.active = True
    reservation.status = 'A'
    reservation.save()
    
    quarto = Room.objects.get(pk=reservation.room.pk)
    quarto.available = False
    quarto.save()

    admin_users = Client.objects.filter(is_staff=True)
    admin_emails = [adm.email for adm in admin_users if adm.email]

    send_mass_mail(
        datatuple=[
            (
                "Agendamento de reserva",
                "Olá, passando pra avisar que a sua reserva agendada ativou!",
                settings.DEFAULT_FROM_EMAIL,
                [reservation.client.email],
            ),
            (
                "Agendamento de reserva",
                f"Olá, passando pra avisar que a reserva agendada de {reservation.client.complete_name} foi ativada!",
                settings.DEFAULT_FROM_EMAIL,
                [admin_emails],
            ),
        ],
        fail_silently=False
    )
