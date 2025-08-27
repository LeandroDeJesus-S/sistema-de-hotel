from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservations'

    def ready(self) -> None:  # noqa: PLR6301
        try:
            from django.db.utils import OperationalError  # noqa: PLC0415
            from django_q.models import Schedule  # noqa: PLC0415

            if not Schedule.objects.filter(name='checar finalização das reservas').exists():
                Schedule.objects.create(
                    func='reservations.tasks.check_reservation_dates',
                    schedule_type=Schedule.DAILY,
                    name='checar finalização das reservas',
                )
        except OperationalError:
            pass
