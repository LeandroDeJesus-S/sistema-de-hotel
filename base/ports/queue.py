from abc import abstractmethod
from datetime import datetime
from typing import Any, Callable, Protocol


class TaskQueuer(Protocol):
    """
    An interface for a task queue scheduler.
    """

    @abstractmethod
    def schedule_task(
        self,
        func_path: str | Callable[[Any], Any],
        run_at: datetime,
        args: tuple,
        name: str | None = None,
        repeats: int = 1,
    ) -> Any:
        """
        Schedules a task to run.

        Args:
            func_path: The path to the function to execute.
            run_at: The datetime for the task to run.
            args: The arguments to pass to the function.
            name: An optional name for the task.
            repeats: The number of times to repeat the task. Defaults to 1 (run once).

        Returns:
            An identifier for the scheduled task.
        """
        ...

    @abstractmethod
    def queue_task(
        self, func_path: str | Callable[[Any], Any], args: tuple, name: str | None = None
    ) -> Any:
        """
        Queues a task to run immediately.

        Args:
            func_path: The path or callable to execute.
            args: The arguments to pass to the function.
            name: An optional name for the task.

        Returns:
            An identifier for the queued task.
        """
        ...
