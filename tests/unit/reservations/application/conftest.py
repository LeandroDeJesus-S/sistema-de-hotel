import pytest
import logging
from unittest.mock import Mock
from base.ports.queue import TaskQueuer
from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from payments.domain.ports import AbsPaymentsRepository
from reservations.domain.repo import AbsReservationRepository, AbsRoomRepository

@pytest.fixture
def mock_reservation_repo():
    return Mock(spec=AbsReservationRepository)

@pytest.fixture
def mock_room_repo():
    return Mock(spec=AbsRoomRepository)

@pytest.fixture
def mock_client_repo():
    return Mock(spec=AbsClientRepository)

@pytest.fixture
def mock_payments_repo():
    return Mock(spec=AbsPaymentsRepository)

@pytest.fixture
def mock_unit_of_work():
    uow = Mock(spec=AbsUnitOfWork)
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)
    return uow

@pytest.fixture
def mock_task_queuer():
    return Mock(spec=TaskQueuer)

@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)
