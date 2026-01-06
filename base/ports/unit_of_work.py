from abc import abstractmethod
from typing import ContextManager, Protocol


class AbsUnitOfWork(ContextManager, Protocol):
    @abstractmethod
    def commit(self):
        """Commits the current unit of work."""
        ...

    @abstractmethod
    def rollback(self):
        """Rolls back the current unit of work."""
        ...
