"""
Tests for reservation cancellation functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.utils import timezone
from ddf import G

from clients.models import Client
from payments.models import Payment
from reservations.application.usecases import CancelReservationUseCase
from reservations.domain.entities import Reservation
from reservations.domain.value_objects import ReservationStatusEnum
from reservations.models import Reservation as ReservationModel, Room
from utils.support import Result


@pytest.mark.django_db
class TestCancelReservationUseCase:
    """Test the CancelReservationUseCase functionality."""

    def test_cancel_active_reservation_success(self):
        """Test successful cancellation of an active reservation."""
        # Setup
        client = G(Client)
        room = G(Room, available=True)
        reservation = G(
            ReservationModel,
            client=client,
            room=room,
            status='A',  # ACTIVE
            checkin=timezone.now().date() + timedelta(days=3),  # 3 days from now
            checkout=timezone.now().date() + timedelta(days=5),
            amount=500.00,
        )
        payment = G(Payment, reservation=reservation, status='completed', amount=500.00)

        # Mock dependencies
        mock_repo = Mock()
        mock_repo.find_by_id.return_value = Result.Ok(reservation)
        mock_repo.save.return_value = Result.Ok(reservation)

        mock_room_repo = Mock()
        mock_room_repo.save.return_value = Result.Ok(reservation.room)

        mock_payments_repo = Mock()
        mock_payments_repo.get_by_reservation_id.return_value = Result.Ok(payment)

        mock_unit_of_work = Mock()
        mock_unit_of_work.__enter__ = Mock(return_value=mock_unit_of_work)
        mock_unit_of_work.__exit__ = Mock(return_value=None)
        mock_task_queuer = Mock()

        # Create use case
        usecase = CancelReservationUseCase(
            reservation_repo=mock_repo,
            room_repo=mock_room_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_unit_of_work,
            task_queuer=mock_task_queuer,
            logger=Mock(),
        )

        # Execute
        result = usecase(reservation.id, client.id, 'Changed plans')

        # Assert
        assert result.is_ok()
        cancelled_reservation = result.unwrap()

        # Check that reservation was updated
        assert cancelled_reservation.status == ReservationStatusEnum.CANCELLED
        assert cancelled_reservation.cancelled_at is not None
        assert cancelled_reservation.cancellation_reason == 'Changed plans'

        # Check that mocks were called
        mock_repo.save.assert_called_once()
        mock_task_queuer.queue_task.assert_called()

    def test_cancel_reservation_too_close_to_checkin(self):
        """Test cancellation fails when too close to check-in."""
        # Setup
        client = G(Client)
        room = G(Room, available=True)
        reservation = G(
            ReservationModel,
            client=client,
            room=room,
            status='A',  # ACTIVE
            checkin=timezone.now().date() + timedelta(hours=12),  # 12 hours from now
            checkout=timezone.now().date() + timedelta(days=2),
        )

        # Mock dependencies
        mock_repo = Mock()
        mock_repo.find_by_id.return_value = Result.Ok(reservation)

        mock_room_repo = Mock()

        mock_payments_repo = Mock()
        mock_unit_of_work = Mock()
        mock_unit_of_work.__enter__ = Mock(return_value=mock_unit_of_work)
        mock_unit_of_work.__exit__ = Mock(return_value=None)
        mock_task_queuer = Mock()

        # Create use case
        usecase = CancelReservationUseCase(
            reservation_repo=mock_repo,
            room_repo=mock_room_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_unit_of_work,
            task_queuer=mock_task_queuer,
            logger=Mock(),
        )

        # Execute
        result = usecase(reservation.id, client.id)

        # Assert
        assert result.is_err()
        assert 'Cancelamentos só são permitidos até 24 horas antes do check-in' in str(
            result.unwrap_err()
        )

    def test_cancel_reservation_wrong_owner(self):
        """Test cancellation fails for wrong owner."""
        # Setup
        client = G(Client)
        wrong_client = G(Client)
        room = G(Room, available=True)
        reservation = G(
            ReservationModel,
            client=client,
            room=room,
            status='A',  # ACTIVE
            checkin=timezone.now().date() + timedelta(days=3),
            checkout=timezone.now().date() + timedelta(days=5),
        )

        # Mock dependencies
        mock_repo = Mock()
        mock_repo.find_by_id.return_value = Result.Ok(reservation)

        mock_room_repo = Mock()

        mock_payments_repo = Mock()
        mock_unit_of_work = Mock()
        mock_unit_of_work.__enter__ = Mock(return_value=mock_unit_of_work)
        mock_unit_of_work.__exit__ = Mock(return_value=None)
        mock_task_queuer = Mock()

        # Create use case
        usecase = CancelReservationUseCase(
            reservation_repo=mock_repo,
            room_repo=mock_room_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_unit_of_work,
            task_queuer=mock_task_queuer,
            logger=Mock(),
        )

        # Execute
        result = usecase(reservation.id, wrong_client.id)

        # Assert
        assert result.is_err()
        assert 'Você não tem permissão para cancelar esta reserva' in str(result.unwrap_err())
