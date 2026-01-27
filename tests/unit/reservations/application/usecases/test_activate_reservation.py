from datetime import date, timedelta
from decimal import Decimal

import pytest

from exc import Result
from reservations.application.usecases import ActivateReservationUseCase
from reservations.domain.value_objects import Currency, PriceValue, ReservationStatusEnum
from reservations.domain.entities import Reservation


class TestActivateReservationUseCase:
    @pytest.fixture
    def use_case(self, mock_reservation_repo, mock_room_repo, mock_unit_of_work, mock_logger):
        return ActivateReservationUseCase(
            reservation_repo=mock_reservation_repo,
            room_repo=mock_room_repo,
            unit_of_work=mock_unit_of_work,
            logger=mock_logger,
        )

    def test_success(
        self,
        use_case,
        mock_reservation_repo,
        mock_room_repo,
        reservation_model_instance_factory,
        client_entity,
        room_entity,
    ):
        """Should successfully activate a reservation and update room availability."""
        # We need a proper entity, not a django model instance from factory directly if the usecase expects entity
        # But wait, the previous tests used factories that returned models. The Domain Entities are Pydantic.
        # The usecase expects Reservation (Pydantic).
        # We should use the fixture 'room_entity' and manually create a reservation entity.

        # Manually creating reservation entity for test
        res = Reservation.safe_create(
            id=1,
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('100.00') * 100),
            status=ReservationStatusEnum.INITIALIZED,
        ).unwrap()

        mock_room_repo.save.return_value = Result.Ok(room_entity)
        mock_reservation_repo.save.return_value = Result.Ok(res)

        result = use_case(res)

        assert result.is_ok()
        saved_res = result.unwrap()
        assert saved_res.status == ReservationStatusEnum.ACTIVE
        assert saved_res.room.available is False

        mock_room_repo.save.assert_called_with(res.room)
        mock_reservation_repo.save.assert_called_with(res)

    def test_room_save_failure(self, use_case, mock_room_repo, client_entity, room_entity):
        """Should fail if the room repository fails to save the room state."""
        res = Reservation.safe_create(
            id=1,
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('100.00') * 100),
            status=ReservationStatusEnum.INITIALIZED,
        ).unwrap()

        mock_room_repo.save.return_value = Result.Err('Room Save Error')

        result = use_case(res)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to save room state'

    def test_reservation_save_failure(
        self, use_case, mock_room_repo, mock_reservation_repo, client_entity, room_entity
    ):
        """Should fail if the reservation repository fails to save the reservation state."""
        res = Reservation.safe_create(
            id=1,
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('100.00') * 100),
            status=ReservationStatusEnum.INITIALIZED,
        ).unwrap()

        mock_room_repo.save.return_value = Result.Ok(room_entity)
        mock_reservation_repo.save.return_value = Result.Err('Res Save Error')

        result = use_case(res)

        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to save reservation'
