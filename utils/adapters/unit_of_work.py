import logging
from typing import Any

from django.db import transaction

from base.ports.unit_of_work import AbsUnitOfWork


class UnitOfWork(AbsUnitOfWork):
    def __init__(
        self, using: Any | None = None, savepoint: bool = True, durable: bool = False
    ):
        self._using = using
        self._savepoint = savepoint
        self._durable = durable
        self._ctx = transaction.atomic(using, savepoint, durable)

    def __enter__(self):
        logging.getLogger('djangoLogger').debug('Enter UOW')
        self._ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.getLogger('djangoLogger').debug('Exit UOW')
        self._ctx.__exit__(exc_type, exc_val, exc_tb)

    def commit(self):
        transaction.commit(self._using)

    def rollback(self):
        transaction.rollback(self._using)
