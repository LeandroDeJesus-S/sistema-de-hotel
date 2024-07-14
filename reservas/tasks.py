from django.utils.timezone import now

from django.core.mail import send_mass_mail
from django.conf import settings
from django.contrib.auth.models import User
from reservas.models import Reserva
from clientes.models import Contato


def check_reservation_dates():
    for reservation in Reserva.objects.filter(quarto__disponivel=False):
        if reservation.checkout >= now().date():
            reservation.quarto.disponivel = True
            reservation.quarto.save()
            
            client_contact = Contato.objects.get(id=reservation.cliente.pk)
            message1 = (
                "Vencimento da reserva",
                "Olá, passando pra avisar que a sua reserva expirou!",
                settings.EMAIL_HOST_USERNAME,
                [client_contact.email],
            )

            admin_users = User.objects.filter(is_staff=True)
            admin_emails = [adm.email for adm in admin_users if adm.email]
            message2 = (
                'Vencimento da reserva',
                f'Reserva de {reservation.cliente.complete_name} para o quarto {reservation.quarto} expirou!',
                settings.EMAIL_HOST_USERNAME,
                admin_emails
            )
            send_mass_mail((message1, message2), fail_silently=False)


def print_schedule_result(schedule_obj):
    print(schedule_obj)
