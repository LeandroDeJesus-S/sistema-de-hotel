from typing import Any

from django.db import transaction

from base.ports.unit_of_work import AbsUnitOfWork


class UnitOfWork(AbsUnitOfWork):
    def __init__(
        self,
        using: Any | None = None,
    ):
        self._using = using

    def __enter__(self):
        transaction.set_autocommit(False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        transaction.set_autocommit(True)

    def commit(self):
        transaction.commit(self._using)

    def rollback(self):
        transaction.rollback(self._using)
