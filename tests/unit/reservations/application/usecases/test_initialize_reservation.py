import pytest
from decimal import Decimal
from datetime import date, timedelta
from exc import Result
from reservations.application.usecases import InitializeReservationUseCase
from reservations.application.dtos import CreateReservationInput
from reservations.domain.value_objects import ReservationStatusEnum
from reservations.feedback_messages import ReservationMessages

class TestInitializeReservationUseCase:
    @pytest.fixture
    def use_case(self, mock_reservation_repo, mock_room_repo, mock_client_repo, mock_unit_of_work, mock_logger):
        return InitializeReservationUseCase(
            reservation_repo=mock_reservation_repo,
            room_repo=mock_room_repo,
            client_repo=mock_client_repo,
            unit_of_work=mock_unit_of_work,
            logger=mock_logger
        )

    def test_success(self, use_case, mock_client_repo, mock_room_repo, mock_reservation_repo, client_entity, room_entity):
        """Should successfully create and save a new reservation when all checks pass."""
        # Arrange
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=3)
        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=checkin,
            check_out=checkout,
            observations="Test reservation"
        )

        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Ok(room_entity)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(False)

        # Mock save to return the same reservation with an ID
        def save_side_effect(reservation):
            reservation.id = 123
            return Result.Ok(reservation)
        mock_reservation_repo.save.side_effect = save_side_effect

        # Act
        result = use_case(input_dto)

        # Assert
        assert result.is_ok()
        reservation = result.unwrap()
        assert reservation.id == 123
        assert reservation.client == client_entity
        assert reservation.room == room_entity
        assert reservation.checkin == checkin
        assert reservation.checkout == checkout
        assert reservation.status == ReservationStatusEnum.INITIALIZED

        # Verify calls
        mock_client_repo.get_by_id.assert_called_with(1)
        mock_room_repo.find_by_id.assert_called_with(1)
        mock_reservation_repo.has_overlapping_reservation.assert_called_with(
            room_id=1, check_in=checkin, check_out=checkout
        )
        mock_reservation_repo.save.assert_called()

    def test_client_not_found(self, use_case, mock_client_repo):
        """Should fail if the client ID provided does not exist."""
        mock_client_repo.get_by_id.return_value = Result.Err("Client not found")
        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=1),
            observations=""
        )

        result = use_case(input_dto)

        assert result.is_err()
        assert result.unwrap_err().msg == "client not found"

    def test_room_not_found(self, use_case, mock_client_repo, mock_room_repo, client_entity):
        """Should fail if the room ID provided does not exist."""
        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Err("Room not found")
        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=1),
            observations=""
        )

        result = use_case(input_dto)

        assert result.is_err()
        assert result.unwrap_err().msg == "room not found"

    def test_overlap(self, use_case, mock_client_repo, mock_room_repo, mock_reservation_repo, client_entity, room_entity):
        """Should fail if there is an overlapping reservation for the selected room and dates."""
        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Ok(room_entity)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(True)

        # Mock from_room chaining for error message. Needs at least one reservation to avoid UnboundLocalError
        from reservations.domain.entities import Reservation
        from decimal import Decimal
        res = Reservation.safe_create(
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100.00"),
            status=ReservationStatusEnum.ACTIVE
        ).unwrap()
        mock_reservation_repo.from_room.return_value = Result.Ok([res])

        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=1),
            observations=""
        )

        result = use_case(input_dto)

        assert result.is_err()
        # The logic tries to get available dates message, if list is empty/fails it defaults
        # But here we just want to ensure it fails due to overlap

    def test_save_failure(self, use_case, mock_client_repo, mock_room_repo, mock_reservation_repo, client_entity, room_entity):
        """Should fail if the repository fails to save the reservation."""
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=3)
        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=checkin,
            check_out=checkout,
            observations=""
        )

        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Ok(room_entity)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(False)
        mock_reservation_repo.save.return_value = Result.Err("DB Error")

        result = use_case(input_dto)

        assert result.is_err()
        assert result.unwrap_err().msg == "failed to save reservation"

    def test_overlap_repo_error(self, use_case, mock_client_repo, mock_room_repo, mock_reservation_repo, client_entity, room_entity):
        """Should fail if has_overlapping_reservation returns error."""
        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Ok(room_entity)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Err("Repo Error")

        # We need mock from_room to return OK to reach the error message logic,
        # because the code enters the block if is_err() OR unwrap() is true.
        # But if is_err() is true, it proceeds to from_room.
        # If from_room succeeds, it returns Err(msg=available_dates_msg).

        # Let's mock from_room to return Ok([res]) to avoid UnboundLocalError in support.py
        from reservations.domain.entities import Reservation
        from decimal import Decimal
        res = Reservation.safe_create(
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100.00"),
            status=ReservationStatusEnum.ACTIVE
        ).unwrap()
        mock_reservation_repo.from_room.return_value = Result.Ok([res])

        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=1),
            observations=""
        )

        result = use_case(input_dto)
        assert result.is_err()
        # It should return the available dates message, which for empty list is specific.
        # But specifically we want to test that it handles the initial error as "overlap found" logic.

    def test_overlap_message_error(self, use_case, mock_client_repo, mock_room_repo, mock_reservation_repo, client_entity, room_entity):
        """Should return generic error if getting available dates message fails."""
        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Ok(room_entity)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(True)

        # Mock from_room to return Err, simulating failure to get other reservations
        mock_reservation_repo.from_room.return_value = Result.Err("DB Error")

        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=1),
            observations=""
        )

        result = use_case(input_dto)
        assert result.is_err()
        assert result.unwrap_err().msg == "The room is not available"

    def test_create_entity_failure(self, use_case, mock_client_repo, mock_room_repo, mock_reservation_repo, client_entity, room_entity, mocker):
        """Should fail if Reservation.safe_create fails."""
        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Ok(room_entity)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(False)

        # Patch Reservation.safe_create to return Err
        mocker.patch(
            'reservations.application.usecases.Reservation.safe_create',
            return_value=Result.Err("Invalid data")
        )

        input_dto = CreateReservationInput(
            client_id=1,
            room_pk=1,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=1),
            observations=""
        )

        result = use_case(input_dto)
        assert result.is_err()
        assert result.unwrap_err().msg == ReservationMessages.RESERVATION_FAIL
