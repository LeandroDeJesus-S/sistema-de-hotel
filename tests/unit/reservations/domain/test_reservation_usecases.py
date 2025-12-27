from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest
from pydantic import ValidationError

from base.ports import unit_of_work
from clients.domain.entities import Client
from exc import Error, Result
from reservations.application.dtos import CreateReservationInput
from reservations.application.usecases import (
    FetchClientActiveReservations,
    FetchClientReservationHistoryUseCase,
    FetchReservationDetailUseCase,
    InitializeReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.domain.entities import Reservation, ReservationStatus, Room
from reservations.domain.repo import AbsReservationRepository, AbsRoomRepository
from payments.domain.ports import AbsPaymentsRepository
from reservations.domain.value_objects import ReservationStatusEnum


@pytest.fixture
def mock_reservation_repo():
    return Mock(spec=AbsReservationRepository)


@pytest.fixture
def mock_room_repo():
    return Mock()


@pytest.fixture
def mock_client_repo():
    return Mock()


@pytest.fixture
def mock_uow():
    return MagicMock()


@pytest.fixture
def mock_payments_repo():
    return Mock()


@pytest.fixture
def mock_client():
    return Mock(spec=Client)


@pytest.fixture
def mock_room():
    room = Mock(spec=Room)
    room.available = True
    room.daily_price = Decimal('100.00')
    return room


class TestInitializeReservationUseCase:
    def test_init(self, mock_reservation_repo, mock_room_repo, mock_client_repo, mock_uow):
        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_uow
        )
        assert uc.reservation_repo == mock_reservation_repo
        assert uc.room_repo == mock_room_repo
        assert uc.client_repo == mock_client_repo
        assert uc.unit_of_work == mock_uow

    def test_call_with_valid_data_returns_reservation(
        self,
        mock_reservation_repo,
        mock_room_repo,
        mock_client_repo,
        mock_uow,
        mock_client,
        mock_room,
    ):
        # Arrange
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=5)
        command = CreateReservationInput(
            client_id=1, room_pk=1, check_in=check_in, check_out=check_out, observations=''
        )

        mock_client_repo.get_by_id.return_value = Result.Ok(mock_client)
        mock_room_repo.find_by_id.return_value = Result.Ok(mock_room)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(False)
        mock_reservation_repo.save.return_value = Result.Ok(Mock(spec=Reservation))

        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_uow
        )

        # Act
        result = uc(command)

        # Assert
        assert result.is_ok()
        assert isinstance(result.unwrap(), Reservation)
        mock_reservation_repo.save.assert_called_once()

    def test_call_with_overlapping_reservation_returns_error(
        self,
        mock_reservation_repo,
        mock_room_repo,
        mock_client_repo,
        mock_uow,
        mock_client,
        mock_room,
    ):
        # Arrange
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=5)
        command = CreateReservationInput(
            client_id=1, room_pk=1, check_in=check_in, check_out=check_out, observations=''
        )

        mock_client_repo.get_by_id.return_value = Result.Ok(mock_client)
        mock_room_repo.find_by_id.return_value = Result.Ok(mock_room)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(True)

        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_uow
        )

        # Act
        result = uc(command)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == 'The room is not available'
        mock_reservation_repo.save.assert_not_called()


class TestFetchClientActiveReservations:
    def test_init(self, mock_reservation_repo):
        uc = FetchClientActiveReservations(mock_reservation_repo)
        assert uc._repo == mock_reservation_repo

    def test_call_returns_list_of_reservations(self, mock_reservation_repo):
        # Arrange
        client_id = 1
        reservations = [
            Mock(spec=Reservation, status=ReservationStatusEnum.ACTIVE),
            Mock(spec=Reservation, status=ReservationStatusEnum.SCHEDULED),
        ]
        mock_reservation_repo.fetch_active_reservations.return_value = Result.Ok(
            reservations
        )
        uc = FetchClientActiveReservations(mock_reservation_repo)

        # Act
        result = uc(client_id, include_scheduled=True)

        # Assert
        assert result.is_ok()
        assert result.unwrap() == reservations
        mock_reservation_repo.fetch_active_reservations.assert_called_once_with(
            client_id, True
        )


class TestReleaseRoomUseCase:
    def test_release_room_successfully(self):
        # given
        mock_uow = MagicMock(spec=unit_of_work.AbsUnitOfWork)
        mock_reservation = MagicMock()
        mock_reservation.status = ReservationStatus.ACTIVE
        mock_reservation.room = MagicMock()

        mock_room_repo = MagicMock(spec=AbsRoomRepository)
        mock_room_repo.save.return_value = Result.Ok(Mock(spec=Room))

        mock_reservations_repo = MagicMock(spec=AbsReservationRepository)
        mock_reservations_repo.save.return_value = Result.Ok(mock_reservation)
        mock_payments_repo = MagicMock(spec=AbsPaymentsRepository)

        use_case = ReleaseReservationUseCase(
            room_repo=mock_room_repo,
            reservations_repo=mock_reservations_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_uow,
        )

        # when
        result = use_case(reservation=mock_reservation)

        # then
        assert result.is_ok(), str(result.unwrap_err())
        mock_uow.__enter__.return_value.commit.assert_called_once()
        assert mock_reservation.status == ReservationStatus.FINISHED
        assert mock_reservation.room.available is True

    def test_return_error_if_room_not_found(self, mock_uow: MagicMock):
        # given
        mock_room_repo = MagicMock(spec=AbsRoomRepository)
        mock_reservations_repo = MagicMock(spec=AbsReservationRepository)
        mock_payments_repo = MagicMock(spec=AbsPaymentsRepository)
        mock_room_repo.save.return_value = Result.Err(msg='db error')

        mock_reservation = MagicMock()
        mock_reservation.room = MagicMock()
        mock_reservation.status = ReservationStatus.ACTIVE

        use_case = ReleaseReservationUseCase(
            room_repo=mock_room_repo,
            reservations_repo=mock_reservations_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_uow,
        )

        # when
        result = use_case(reservation=mock_reservation)

        # then
        assert result.is_err()
        assert "Failed to save reservation" in result.unwrap_err().msg
        mock_uow.__enter__.return_value.rollback.assert_called_once()

    def test_return_error_if_saving_room_fails(self, mock_uow: MagicMock):
        # given
        mock_reservation = MagicMock()
        mock_reservation.status = ReservationStatus.ACTIVE
        mock_reservation.room = MagicMock()
        mock_room_repo = MagicMock(spec=AbsRoomRepository)
        mock_reservations_repo = MagicMock(spec=AbsReservationRepository)
        mock_reservations_repo.save.return_value = Result.Err(msg="Database error")
        mock_payments_repo = MagicMock(spec=AbsPaymentsRepository)

        mock_reservation.status = ReservationStatus.ACTIVE
        mock_reservation.room = MagicMock()

        use_case = ReleaseReservationUseCase(
            room_repo=mock_room_repo,
            reservations_repo=mock_reservations_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_uow,
        )

        # when
        result = use_case(reservation=mock_reservation)

        # then
        assert result.is_err()
        assert "Failed to save reservation for releasing" in result.unwrap_err().msg
        mock_uow.__enter__.return_value.rollback.assert_called_once()


class TestFetchClientReservationHistoryUseCase:
    def test_call_returns_reservation_history(self, mock_reservation_repo):
        # Arrange
        client_id = 1
        history = [Mock(spec=Reservation), Mock(spec=Reservation)]
        mock_reservation_repo.fetch_client_history.return_value = Result.Ok(history)
        uc = FetchClientReservationHistoryUseCase(mock_reservation_repo)

        # Act
        result = uc(client_id)

        # Assert
        assert result.is_ok()
        assert result.unwrap() == history
        mock_reservation_repo.fetch_client_history.assert_called_once_with(client_id)


class TestFetchReservationDetailUseCase:
    def test_call_returns_reservation_detail(self, mock_reservation_repo):
        # Arrange
        reservation_id = 1
        client_id = 1
        reservation = Mock(spec=Reservation)
        mock_reservation_repo.fetch_for_history_detail.return_value = Result.Ok(
            reservation
        )
        uc = FetchReservationDetailUseCase(mock_reservation_repo)

        # Act
        result = uc(reservation_id, client_id)

        # Assert
        assert result.is_ok()
        assert result.unwrap() == reservation
        mock_reservation_repo.fetch_for_history_detail.assert_called_once_with(
            client_id, reservation_id
        )


class TestScheduleReservationUseCase:
    def test_schedule_reservation_successfully(self, mock_reservation_repo, mock_uow):
        # Arrange
        mock_task_queuer = Mock()
        use_case = ScheduleReservationUseCase(
            reservation_repo=mock_reservation_repo,
            unit_of_work=mock_uow,
            task_queuer=mock_task_queuer,
        )

        mock_reservation = MagicMock(spec=Reservation)
        mock_reservation.id = 123
        mock_reservation.checkin = date.today()
        mock_reservation.status = ReservationStatusEnum.INITIALIZED

        mock_reservation_repo.save.return_value = Result.Ok(mock_reservation)

        # Act
        result = use_case(mock_reservation)

        # Assert
        assert result.is_ok()
        assert mock_reservation.status == ReservationStatusEnum.SCHEDULED

        # Verify activation task was scheduled
        mock_task_queuer.schedule_task.assert_called_once()
        args, kwargs = mock_task_queuer.schedule_task.call_args
        assert kwargs['func_path'] == 'reservations.infra.tasks.activate_reservation_task'
        assert kwargs['args'] == (123,)

        # Verify email notification was queued
        mock_task_queuer.queue_task.assert_called_once()
        args, kwargs = mock_task_queuer.queue_task.call_args
        assert args[0] == 'reservations.infra.tasks.send_scheduling_notification'
        assert args[1] == (123,)

        # Verify transaction commit
        mock_uow.__enter__.return_value.commit.assert_called_once()
