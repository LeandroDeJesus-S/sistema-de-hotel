import pytest
from unittest.mock import Mock
from exc import Result
from reservations.application.usecases import (
    FetchClientActiveReservations,
    FetchClientReservationHistoryUseCase,
    FetchReservationDetailUseCase
)

class TestFetchClientActiveReservations:
    def test_call_delegates_to_repo(self, mock_reservation_repo):
        """Should delegate the call to repository's fetch_active_reservations."""
        use_case = FetchClientActiveReservations(mock_reservation_repo)
        expected_result = Result.Ok([Mock()])
        mock_reservation_repo.fetch_active_reservations.return_value = expected_result

        result = use_case(client_id=1, include_scheduled=True)

        assert result == expected_result
        mock_reservation_repo.fetch_active_reservations.assert_called_once_with(1, True)

class TestFetchClientReservationHistoryUseCase:
    def test_call_delegates_to_repo(self, mock_reservation_repo):
        """Should delegate the call to repository's fetch_client_history."""
        use_case = FetchClientReservationHistoryUseCase(mock_reservation_repo)
        expected_result = Result.Ok([Mock()])
        mock_reservation_repo.fetch_client_history.return_value = expected_result

        result = use_case(client_id=1)

        assert result == expected_result
        mock_reservation_repo.fetch_client_history.assert_called_once_with(1)

class TestFetchReservationDetailUseCase:
    def test_call_delegates_to_repo(self, mock_reservation_repo):
        """Should delegate the call to repository's fetch_for_history_detail."""
        use_case = FetchReservationDetailUseCase(mock_reservation_repo)
        expected_result = Result.Ok(Mock())
        mock_reservation_repo.fetch_for_history_detail.return_value = expected_result

        result = use_case(reservation_id=10, client_id=1)

        assert result == expected_result
        mock_reservation_repo.fetch_for_history_detail.assert_called_once_with(1, 10)
