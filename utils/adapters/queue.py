from datetime import datetime
from typing import Any, Callable

from django_q.tasks import async_task, schedule

from base.ports.queue import TaskQueuer


class DjangoQTaskQueuer(TaskQueuer):
    """
    A concrete implementation of the TaskQueuer port using Django Q.
    """

    def schedule_task(  # noqa: PLR6301
        self,
        func_path: str | Callable[[Any], Any],
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

    def queue_task(  # noqa: PLR6301
        self, func_path: str | Callable[[Any], Any], args: tuple, name: str | None = None
    ) -> Any:
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
