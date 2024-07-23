from django.apps import AppConfig
from django.db.utils import IntegrityError
import logging as log


class ReservasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservas'

    def ready(self) -> None:
        if hasattr(self, '__task'): return

        from django_q.tasks import async_task
        from .tasks import check_reservation_dates

        try:
            async_task(
                check_reservation_dates, 
                task_name='check_reservation_dates',
            )
        except IntegrityError as e:
            log.warning(str(e))
