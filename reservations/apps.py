from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservations'

    def ready(self) -> None:  # noqa: PLR6301
        from HOTEL import settings  # noqa: PLC0415

        from .container import ReservationsContainer  # noqa: PLC0415

        reservations_container = ReservationsContainer()
        reservations_container.config.from_dict(settings.__dict__)
        reservations_container.wire(modules=['.views', '.infra.tasks', '.tasks'])
        try:
            from django.db.utils import OperationalError  # noqa: PLC0415
            from django_q.models import Schedule  # noqa: PLC0415

            if not Schedule.objects.filter(name='checar finalização das reservas').exists():
                Schedule.objects.create(
                    func='reservations.infra.tasks.check_reservation_dates_task',
                    schedule_type=Schedule.DAILY,
                    name='checar finalização das reservas',
                )
        except OperationalError:
            pass
