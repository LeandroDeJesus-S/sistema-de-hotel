import pytest
from unittest.mock import ANY
from exc import Result
from reservations.application.usecases import ScheduleReservationUseCase
from reservations.domain.value_objects import Currency, PriceValue, ReservationStatusEnum
from reservations.domain.entities import Reservation


class TestScheduleReservationUseCase:
    @pytest.fixture
    def use_case(
        self, mock_reservation_repo, mock_unit_of_work, mock_task_queuer, mock_logger
    ):
        return ScheduleReservationUseCase(
            reservation_repo=mock_reservation_repo,
            unit_of_work=mock_unit_of_work,
            task_queuer=mock_task_queuer,
            logger=mock_logger,
        )

    def test_success(
        self, use_case, mock_reservation_repo, mock_task_queuer, client_entity, room_entity
    ):
        from datetime import date, timedelta
        from decimal import Decimal

        res = Reservation.safe_create(
            id=1,
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.INITIALIZED,
        ).unwrap()

        mock_reservation_repo.save.return_value = Result.Ok(res)

        result = use_case(res)

        assert result.is_ok()
        saved_res = result.unwrap()
        assert saved_res.status == ReservationStatusEnum.SCHEDULED

        mock_reservation_repo.save.assert_called_with(res)

        # Verify tasks scheduled
        mock_task_queuer.schedule_task.assert_called_once()
        mock_task_queuer.queue_task.assert_called_once()  # Notification

    def test_save_failure(self, use_case, mock_reservation_repo, client_entity, room_entity):
        from datetime import date, timedelta
        from decimal import Decimal

        res = Reservation.safe_create(
            id=1,
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.INITIALIZED,
        ).unwrap()

        mock_reservation_repo.save.return_value = Result.Err('Save Error')

        result = use_case(res)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to save reservation for scheduling'
