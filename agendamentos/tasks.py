from .models import Agendamento
from django.core.mail import send_mass_mail
from django.conf import settings
from clientes.models import Cliente
from reservas.models import Reserva, Quarto


def schedule_reservation(reservation_id):
    reserva = Reserva.objects.get(pk=int(reservation_id))
    reserva.ativa = True
    reserva.status = 'A'
    reserva.save()
    
    quarto = Quarto.objects.get(pk=reserva.quarto.pk)
    quarto.disponivel = False
    quarto.save()

    admin_users = Cliente.objects.filter(is_staff=True)
    admin_emails = [adm.email for adm in admin_users if adm.email]

    send_mass_mail(
        datatuple=[
            (
                "Agendamento de reserva",
                "Olá, passando pra avisar que a sua reserva agendada ativou!",
                settings.DEFAULT_FROM_EMAIL,
                [reserva.cliente.email],
            ),
            (
                "Agendamento de reserva",
                f"Olá, passando pra avisar que a reserva agendada de {reserva.cliente.complete_name} foi ativada!",
                settings.DEFAULT_FROM_EMAIL,
                [admin_emails],
            ),
        ],
        fail_silently=False
    )
