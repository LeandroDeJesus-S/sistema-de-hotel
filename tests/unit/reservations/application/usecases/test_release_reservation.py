import pytest
from exc import Result
from reservations.application.usecases import ReleaseReservationUseCase
from reservations.domain.value_objects import Currency, PriceValue, ReservationStatusEnum
from reservations.domain.entities import Reservation


class TestReleaseReservationUseCase:
    @pytest.fixture
    def use_case(
        self,
        mock_room_repo,
        mock_reservation_repo,
        mock_payments_repo,
        mock_unit_of_work,
        mock_logger,
    ):
        return ReleaseReservationUseCase(
            room_repo=mock_room_repo,
            reservations_repo=mock_reservation_repo,
            payments_repo=mock_payments_repo,
            unit_of_work=mock_unit_of_work,
            logger=mock_logger,
        )

    def test_success(
        self, use_case, mock_reservation_repo, mock_room_repo, client_entity, room_entity
    ):
        from datetime import date, timedelta
        from decimal import Decimal

        res = Reservation.safe_create(
            id=1,
            checkin=date.today(),
            checkout=date.today() + timedelta(days=2),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.ACTIVE,
        ).unwrap()
        res.room.available = False

        mock_reservation_repo.save.return_value = Result.Ok(res)
        mock_room_repo.save.return_value = Result.Ok(room_entity)

        result = use_case(res)

        assert result.is_ok()
        assert result.unwrap() is True
        assert res.status == ReservationStatusEnum.FINISHED
        assert res.room.available is True

        mock_reservation_repo.save.assert_called_with(res)
        mock_room_repo.save.assert_called_with(res.room)

    def test_reservation_save_failure(
        self, use_case, mock_reservation_repo, client_entity, room_entity
    ):
        from datetime import date, timedelta
        from decimal import Decimal

        res = Reservation.safe_create(
            id=1,
            checkin=date.today(),
            checkout=date.today() + timedelta(days=2),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.ACTIVE,
        ).unwrap()

        mock_reservation_repo.save.return_value = Result.Err('Save failed')

        result = use_case(res)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to save reservation for releasing'

    def test_room_save_failure(
        self, use_case, mock_reservation_repo, mock_room_repo, client_entity, room_entity
    ):
        from datetime import date, timedelta
        from decimal import Decimal

        res = Reservation.safe_create(
            id=1,
            checkin=date.today(),
            checkout=date.today() + timedelta(days=2),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('200.00') * 100),
            status=ReservationStatusEnum.ACTIVE,
        ).unwrap()

        mock_reservation_repo.save.return_value = Result.Ok(res)
        mock_room_repo.save.return_value = Result.Err('Room save failed')

        result = use_case(res)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to save room state'
