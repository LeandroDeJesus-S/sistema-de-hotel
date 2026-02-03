import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, ANY
from exc import Result
from reservations.application.usecases import CancelReservationUseCase
from reservations.domain.value_objects import Currency, PriceValue, ReservationStatusEnum
from reservations.feedback_messages import ReservationMessages
from reservations.domain.entities import Reservation


class TestCancelReservationUseCase:
    @pytest.fixture
    def use_case(
        self,
        mock_room_repo,
        mock_reservation_repo,
        mock_payments_repo,
        mock_unit_of_work,
        mock_task_queuer,
        mock_logger,
    ):
        return CancelReservationUseCase(
            room_repo=mock_room_repo,
            reservation_repo=mock_reservation_repo,  # Changed from reservations_repo
            payments_repo=mock_payments_repo,
            unit_of_work=mock_unit_of_work,
            task_queuer=mock_task_queuer,
            logger=mock_logger,
        )

    def test_reservation_not_found(self, use_case, mock_reservation_repo):
        mock_reservation_repo.find_by_id.return_value = Result.Err('Not found')
        result = use_case(reservation_id=1, client_id=1)
        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.RESERVATION_NOT_FOUND

    def test_unauthorized_cancellation(
        self, use_case, mock_reservation_repo, client_entity, room_entity
    ):
        # Reservation belongs to client with id=99, but requested by id=1
        client_entity.id = 99
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)

        result = use_case(reservation_id=1, client_id=1)  # ID mismatch

        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.UNAUTHORIZED_CANCELLATION

    def test_cannot_cancel_status(
        self, use_case, mock_reservation_repo, client_entity, room_entity
    ):
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.FINISHED,  # Cannot cancel finished
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.CANNOT_CANCEL_RESERVATION

    def test_cancellation_too_late(
        self, use_case, mock_reservation_repo, client_entity, room_entity
    ):
        client_entity.id = 1
        # Checkin is today, effectively less than 24h from now
        checkin = datetime.now(timezone.utc)
        res = Reservation.safe_create(
            id=1,
            checkin=checkin,
            checkout=checkin + timedelta(days=2),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.ACTIVE,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.CANCELLATION_TOO_LATE

    def test_success_cancel_scheduled(
        self,
        use_case,
        mock_reservation_repo,
        mock_payments_repo,
        client_entity,
        room_entity,
        mock_task_queuer,
    ):
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Ok(res)

        # Mock payment for refund
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.status = 'completed'
        mock_payment.price = 20000
        mock_payments_repo.get_by_reservation_id.return_value = Result.Ok(mock_payment)

        result = use_case(reservation_id=1, client_id=1, reason='Change of plans')

        assert result.is_ok()
        assert res.status == ReservationStatusEnum.CANCELLED
        assert res.cancellation_reason == 'Change of plans'

        mock_reservation_repo.save.assert_called_with(res)
        # Verify refund triggered
        mock_task_queuer.queue_task.assert_any_call(
            'payments.infra.tasks.process_refund', ANY, name=ANY
        )

    def test_cancel_active_reservation_success(
        self,
        use_case,
        mock_reservation_repo,
        mock_room_repo,
        mock_payments_repo,
        client_entity,
        room_entity,
        mock_task_queuer,
    ):
        """Should successfully cancel an ACTIVE reservation and restore room availability."""
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.ACTIVE,
        ).unwrap()
        res.room.available = False

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Ok(res)
        mock_room_repo.save.return_value = Result.Ok(res.room)
        mock_payments_repo.get_by_reservation_id.return_value = Result.Err('No payment')

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_ok()
        assert res.status == ReservationStatusEnum.CANCELLED
        assert res.room.available is True
        mock_room_repo.save.assert_called_with(res.room)

    def test_cancel_active_room_save_failure(
        self,
        use_case,
        mock_reservation_repo,
        mock_room_repo,
        client_entity,
        room_entity,
        mock_unit_of_work,
    ):
        """Should fail if restoring room availability fails."""
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.ACTIVE,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_room_repo.save.return_value = Result.Err('DB Error')

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to restore room availability'
        mock_unit_of_work.rollback.assert_called()

    def test_cancel_reservation_save_failure(
        self, use_case, mock_reservation_repo, client_entity, room_entity, mock_unit_of_work
    ):
        """Should fail if saving cancelled reservation fails."""
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Err('DB Error')

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to cancel reservation'
        mock_unit_of_work.rollback.assert_called()

    def test_cancel_no_payment(
        self, use_case, mock_reservation_repo, mock_payments_repo, client_entity, room_entity
    ):
        """Should succeed even if no payment is found (refund skipped)."""
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Ok(res)
        mock_payments_repo.get_by_reservation_id.return_value = Result.Err('Not found')

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_ok()

    def test_cancel_payment_not_completed(
        self,
        use_case,
        mock_reservation_repo,
        mock_payments_repo,
        client_entity,
        room_entity,
        mock_task_queuer,
    ):
        """Should succeed but skip refund if payment is not completed."""
        client_entity.id = 1
        res = Reservation.safe_create(
            id=1,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Ok(res)

        mock_payment = Mock()
        mock_payment.status = 'pending'
        mock_payments_repo.get_by_reservation_id.return_value = Result.Ok(mock_payment)

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_ok()
        # Ensure refund task NOT called
        calls = [c.args[0] for c in mock_task_queuer.queue_task.call_args_list]
        assert 'payments.infra.tasks.process_refund' not in calls

    def test_cancel_no_id_refund_skipped(
        self, use_case, mock_reservation_repo, mock_logger, client_entity, room_entity
    ):
        """Should skip refund and log warning if reservation has no ID."""
        client_entity.id = 1
        res = Reservation.safe_create(
            id=None,
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Ok(res)

        result = use_case(reservation_id=1, client_id=1)

        assert result.is_ok()
        mock_logger.warning.assert_called_with('Reservation has no ID, cannot process refund')

    def test_calculate_refund_price(self, use_case, client_entity, room_entity):
        """Should calculate full refund if > 24h and partial if < 24h."""
        payment = Mock()
        payment.price = 10000

        # 1. Full refund (> 24h)
        res_full = Reservation.safe_create(
            checkin=datetime.now(timezone.utc) + timedelta(days=10),
            checkout=datetime.now(timezone.utc) + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=10000,
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        refund_full = use_case._calculate_refund_price(res_full, payment)
        assert refund_full == 10000

        # 2. Partial refund (< 24h)
        res_partial = Reservation.safe_create(
            checkin=datetime.now(timezone.utc),
            checkout=datetime.now(timezone.utc) + timedelta(days=2),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=10000,
            status=ReservationStatusEnum.SCHEDULED,
        ).unwrap()

        refund_partial = use_case._calculate_refund_price(res_partial, payment)
        assert refund_partial == 5000

    def test_send_notifications(self, use_case, mocker):
        """Should call task queuer to send cancellation notification."""
        reservation = mocker.Mock()
        reservation.id = 123

        result = use_case._send_notifications(reservation)

        assert result.is_ok()
        assert result.unwrap() == reservation
        use_case._task_queuer.queue_task.assert_called_with(
            'reservations.infra.tasks.send_cancellation_notification',
            (123,),
            name='send_cancellation_notification_123',
        )
