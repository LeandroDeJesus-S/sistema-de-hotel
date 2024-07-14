from django.apps import AppConfig


class ReservasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservas'

    def ready(self) -> None:
        if hasattr(self, '__task'): return

        from django_q.tasks import schedule
        from .tasks import check_reservation_dates, print_schedule_result

        self.__task = schedule(
            check_reservation_dates, 
            name='check_reservation_dates',
            hook=print_schedule_result,
            repeats=-1,
            schedule_type='I',
            minutes=3
        )
