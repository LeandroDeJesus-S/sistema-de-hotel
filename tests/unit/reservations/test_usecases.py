from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest
from pydantic import ValidationError

from clients.domain.entities import Client
from exc import Error, Result
from reservations.application.dtos import CreateReservationInput
from reservations.application.usecases import (
    FetchClientActiveReservations,
    FetchClientReservationHistoryUseCase,
    FetchReservationDetailUseCase,
    InitializeReservationUseCase,
    ReleaseRoomUseCase,
)
from reservations.domain.entities import Reservation, Room
from reservations.domain.repo import AbsReservationRepository
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
def mock_unit_of_work():
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
    def test_init(self, mock_reservation_repo, mock_room_repo, mock_client_repo, mock_unit_of_work):
        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_unit_of_work
        )
        assert uc.reservation_repo == mock_reservation_repo
        assert uc.room_repo == mock_room_repo
        assert uc.client_repo == mock_client_repo
        assert uc.unit_of_work == mock_unit_of_work

    def test_call_with_valid_data_returns_reservation(
        self,
        mock_reservation_repo,
        mock_room_repo,
        mock_client_repo,
        mock_unit_of_work,
        mock_client,
        mock_room,
    ):
        # Arrange
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=5)
        command = CreateReservationInput(
            client_id=1, room_pk=1, check_in=check_in, check_out=check_out, observations=''
        )

        mock_client_repo.get_by_id.return_value = Result(value=mock_client, error=None)
        mock_room_repo.find_by_id.return_value = Result(value=mock_room, error=None)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result(
            value=False, error=None
        )
        mock_reservation_repo.save.return_value = Result(
            value=Mock(spec=Reservation), error=None
        )
        mock_room_repo.save.return_value = Result(value=mock_room, error=None)

        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_unit_of_work
        )

        # Act
        result = uc(command)

        # Assert
        assert result.error is None
        assert isinstance(result.value, Reservation)
        mock_reservation_repo.save.assert_called_once()
        mock_room_repo.save.assert_called_once()
        assert mock_room.available is False

    def test_call_with_unavailable_room_returns_error(
        self,
        mock_reservation_repo,
        mock_room_repo,
        mock_client_repo,
        mock_unit_of_work,
        mock_client,
        mock_room,
    ):
        # Arrange
        mock_room.available = False
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=5)
        command = CreateReservationInput(
            client_id=1, room_pk=1, check_in=check_in, check_out=check_out, observations=''
        )

        mock_client_repo.get_by_id.return_value = Result(value=mock_client, error=None)
        mock_room_repo.find_by_id.return_value = Result(value=mock_room, error=None)

        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_unit_of_work
        )

        # Act
        result = uc(command)

        # Assert
        assert result.error is not None
        assert result.error.msg == 'room not available'
        mock_reservation_repo.save.assert_not_called()

    def test_call_with_overlapping_reservation_returns_error(
        self,
        mock_reservation_repo,
        mock_room_repo,
        mock_client_repo,
        mock_unit_of_work,
        mock_client,
        mock_room,
    ):
        # Arrange
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=5)
        command = CreateReservationInput(
            client_id=1, room_pk=1, check_in=check_in, check_out=check_out, observations=''
        )

        mock_client_repo.get_by_id.return_value = Result(value=mock_client, error=None)
        mock_room_repo.find_by_id.return_value = Result(value=mock_room, error=None)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result(
            value=True, error=None
        )

        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_unit_of_work
        )

        # Act
        result = uc(command)

        # Assert
        assert result.error is not None
        assert result.error.msg == 'The room is not available'
        mock_reservation_repo.save.assert_not_called()

    def test_call_with_invalid_dates_returns_error(
        self,
        mock_reservation_repo,
        mock_room_repo,
        mock_client_repo,
        mock_unit_of_work,
        mock_client,
        mock_room,
    ):
        # Arrange
        check_in = date.today() - timedelta(days=1)  # Invalid check-in
        check_out = check_in + timedelta(days=5)
        command = CreateReservationInput(
            client_id=1, room_pk=1, check_in=check_in, check_out=check_out, observations=''
        )

        mock_client_repo.get_by_id.return_value = Result(value=mock_client, error=None)
        mock_room_repo.find_by_id.return_value = Result(value=mock_room, error=None)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result(
            value=False, error=None
        )

        uc = InitializeReservationUseCase(
            mock_reservation_repo, mock_room_repo, mock_client_repo, mock_unit_of_work
        )

        # Act
        result = uc(command)

        # Assert
        assert result.error is not None


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
        mock_reservation_repo.fetch_active_reservations.return_value = Result(
            value=reservations, error=None
        )
        uc = FetchClientActiveReservations(mock_reservation_repo)

        # Act
        result = uc(client_id, include_scheduled=True)

        # Assert
        assert result.error is None
        assert result.value == reservations
        mock_reservation_repo.fetch_active_reservations.assert_called_once_with(
            client_id, True
        )


class TestReleaseRoomUseCase:
    def test_release_unpaid_reservation_successfully(
        self,
        mock_room_repo,
        mock_reservation_repo,
        mock_payments_repo,
        mock_unit_of_work,
    ):
        # Arrange
        room = Mock(spec=Room, available=False)
        reservation = Mock(spec=Reservation, room=room)
        mock_reservation_repo.find_by_id.return_value = Result(value=reservation, error=None)
        mock_payments_repo.confirm_reservation_payment.return_value = Result(
            value=False, error=None
        )  # Unpaid
        mock_room_repo.save.return_value = Result(value=None, error=None)
        mock_reservation_repo.save.return_value = Result(value=None, error=None)

        uc = ReleaseRoomUseCase(
            mock_room_repo, mock_reservation_repo, mock_payments_repo, mock_unit_of_work
        )

        # Act
        result = uc(reservation_id=1)

        # Assert
        assert result.error is None
        assert result.value is True
        assert reservation.room.available is True
        assert reservation.status == ReservationStatusEnum.CANCELLED
        mock_room_repo.save.assert_called_once_with(room)
        mock_reservation_repo.save.assert_called_once_with(reservation)

    def test_do_nothing_if_reservation_is_paid(
        self,
        mock_room_repo,
        mock_reservation_repo,
        mock_payments_repo,
        mock_unit_of_work,
    ):
        # Arrange
        room = Mock(spec=Room, available=False)
        reservation = Mock(spec=Reservation, room=room)
        mock_reservation_repo.find_by_id.return_value = Result(value=reservation, error=None)
        mock_payments_repo.confirm_reservation_payment.return_value = Result(
            value=True, error=None
        )  # Paid

        uc = ReleaseRoomUseCase(
            mock_room_repo, mock_reservation_repo, mock_payments_repo, mock_unit_of_work
        )

        # Act
        result = uc(reservation_id=1)

        # Assert
        assert result.error is None
        assert result.value is True
        assert room.available is False  # Should not change
        mock_room_repo.save.assert_not_called()
        mock_reservation_repo.save.assert_not_called()

    def test_return_error_if_reservation_not_found(
        self,
        mock_room_repo,
        mock_reservation_repo,
        mock_payments_repo,
        mock_unit_of_work,
    ):
        # Arrange
        mock_reservation_repo.find_by_id.return_value = Result(value=None, error=Error('not found'))

        uc = ReleaseRoomUseCase(
            mock_room_repo, mock_reservation_repo, mock_payments_repo, mock_unit_of_work
        )

        # Act
        result = uc(reservation_id=999)

        # Assert
        assert result.error is not None
        assert result.value is False
        assert 'not found' in result.error.msg


class TestFetchClientReservationHistoryUseCase:
    def test_call_returns_reservation_history(self, mock_reservation_repo):
        # Arrange
        client_id = 1
        history = [Mock(spec=Reservation), Mock(spec=Reservation)]
        mock_reservation_repo.fetch_client_history.return_value = Result(
            value=history, error=None
        )
        uc = FetchClientReservationHistoryUseCase(mock_reservation_repo)

        # Act
        result = uc(client_id)

        # Assert
        assert result.error is None
        assert result.value == history
        mock_reservation_repo.fetch_client_history.assert_called_once_with(client_id)


class TestFetchReservationDetailUseCase:
    def test_call_returns_reservation_detail(self, mock_reservation_repo):
        # Arrange
        reservation_id = 1
        client_id = 1
        reservation = Mock(spec=Reservation)
        mock_reservation_repo.fetch_for_history_detail.return_value = Result(
            value=reservation, error=None
        )
        uc = FetchReservationDetailUseCase(mock_reservation_repo)

        # Act
        result = uc(reservation_id, client_id)

        # Assert
        assert result.error is None
        assert result.value == reservation
        mock_reservation_repo.fetch_for_history_detail.assert_called_once_with(
            client_id, reservation_id
        )
