import pytest
from datetime import datetime, date, timedelta, time, timezone
from decimal import Decimal
from unittest.mock import Mock, ANY
from exc import Result
from reservations.application.usecases import CancelReservationUseCase
from reservations.domain.value_objects import ReservationStatusEnum
from reservations.feedback_messages import ReservationMessages
from reservations.domain.entities import Reservation

class TestCancelReservationUseCase:
    @pytest.fixture
    def use_case(self, mock_reservation_repo, mock_room_repo, mock_payments_repo, mock_unit_of_work, mock_task_queuer, mock_logger):
        return CancelReservationUseCase(
            reservation_repo=mock_reservation_repo,
            room_repo=mock_room_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_unit_of_work,
            task_queuer=mock_task_queuer,
            logger=mock_logger
        )

    def test_reservation_not_found(self, use_case, mock_reservation_repo):
        mock_reservation_repo.find_by_id.return_value = Result.Err("Not found")
        result = use_case(reservation_id=1, client_id=1)
        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.RESERVATION_NOT_FOUND

    def test_unauthorized_cancellation(self, use_case, mock_reservation_repo, client_entity, room_entity):
        # Reservation belongs to client with id=99, but requested by id=1
        client_entity.id = 99
        res = Reservation.safe_create(
            id=1,
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("200.00"),
            status=ReservationStatusEnum.SCHEDULED
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)

        result = use_case(reservation_id=1, client_id=1) # ID mismatch

        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.UNAUTHORIZED_CANCELLATION

    def test_cannot_cancel_status(self, use_case, mock_reservation_repo, client_entity, room_entity):
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("200.00"),
            status=ReservationStatusEnum.FINISHED # Cannot cancel finished
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.CANNOT_CANCEL_RESERVATION

    def test_cancellation_too_late(self, use_case, mock_reservation_repo, client_entity, room_entity):
        client_entity.id = 1
        # Checkin is today, effectively less than 24h from now
        checkin = date.today()
        res = Reservation.safe_create(
            id=1,
            checkin=checkin,
            checkout=checkin + timedelta(days=2),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("200.00"),
            status=ReservationStatusEnum.ACTIVE
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)

        # We need to make sure timezone.now() vs checkin logic triggers the error
        # Implementation: if checkin_datetime - now < timedelta(hours=24): return Err
        # Since checkin is today (midnight), and now is likely > midnight, the diff is negative or small.

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.CANCELLATION_TOO_LATE

    def test_success_cancel_scheduled(self, use_case, mock_reservation_repo, mock_payments_repo, client_entity, room_entity, mock_task_queuer):
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("200.00"),
            status=ReservationStatusEnum.SCHEDULED
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Ok(res)

        # Mock payment for refund
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.status = 'completed'
        mock_payment.amount = Decimal("200.00")
        mock_payments_repo.get_by_reservation_id.return_value = Result.Ok(mock_payment)

        result = use_case(reservation_id=1, client_id=1, reason="Change of plans")

        assert result.is_ok()
        assert res.status == ReservationStatusEnum.CANCELLED
        assert res.cancellation_reason == "Change of plans"

        mock_reservation_repo.save.assert_called_with(res)
        # Verify refund triggered
        mock_task_queuer.queue_task.assert_any_call(
            'payments.infra.tasks.process_refund', ANY, name=ANY
        )
