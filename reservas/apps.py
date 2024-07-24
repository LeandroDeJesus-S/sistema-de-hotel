from django.apps import AppConfig


class ReservasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservas'

    def ready(self) -> None:
        from django_q.models import Schedule

        if not Schedule.objects.filter(name='checar finalização das reservas').exists():
            Schedule.objects.create(
                func='reservas.tasks.check_reservation_dates',
                schedule_type=Schedule.MINUTES,
                minutes=5,
                name='checar finalização das reservas',
            )
