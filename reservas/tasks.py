from django.utils.timezone import now

from django.core.mail import send_mass_mail
from django.conf import settings
from clientes.models import Cliente
from reservas.models import Reserva


def check_reservation_dates():
    for reservation in Reserva.objects.filter(ativa=True):
        if reservation.checkout >= now().date():
            reservation.quarto.disponivel = True
            reservation.ativa = False
            reservation.quarto.save()
            reservation.save()
            print(f'{reservation} encerrada. Quarto {reservation.quarto} liberado para novas reservas.')
            message1 = (
                "Vencimento da reserva",
                "Olá, passando pra avisar que a sua reserva expirou!",
                settings.DEFAULT_FROM_EMAIL,
                [reservation.cliente.email],
            )

            admin_users = Cliente.objects.filter(is_staff=True)
            admin_emails = [adm.email for adm in admin_users if adm.email]
            message2 = (
                'Vencimento da reserva',
                f'Reserva de {reservation.cliente.complete_name} para o quarto {reservation.quarto} expirou!',
                settings.DEFAULT_FROM_EMAIL,
                admin_emails
            )
            send_mass_mail((message1, message2), fail_silently=False)
