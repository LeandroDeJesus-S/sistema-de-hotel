from datetime import datetime
from typing import Any

from django_q.tasks import async_task, schedule

from reservations.domain.ports import TaskQueuer


class DjangoQTaskQueuer(TaskQueuer):
    """
    A concrete implementation of the TaskQueuer port using Django Q.
    """

    def schedule_task(  # noqa: PLR6301
        self,
        func_path: str,
        run_at: datetime,
        args: tuple,
        name: str | None = None,
        repeats: int = 1,
    ) -> Any:
        """
        Schedules a task using django-q.
        """
        return schedule(
            func_path,
            *args,
            next_run=run_at,
            repeats=repeats,
            name=name,
        )

    def queue_task(self, func_path: str, args: tuple, name: str | None = None) -> Any:  # noqa: PLR6301
        """
        Queues a task to run immediately using django-q.
        Note: The 'name' parameter is not directly supported by async_task in the same
        way it is for scheduled tasks. The task's name will be used as group name instead.
        """
        return async_task(
            func_path,
            *args,
            group=name,
        )
