import pytest
from datetime import date, timedelta
from decimal import Decimal

from exc import Result
from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from reservations.application.services import ReservationService
from reservations.domain.entities import Reservation
from reservations.domain.value_objects import ReservationStatusEnum
from reservations.feedback_messages import ReservationMessages

class TestReservationService:
    @pytest.fixture
    def service(self, mock_reservation_repo, mock_room_repo, mock_client_repo, mock_payments_repo, mock_unit_of_work, mock_task_queuer, mock_logger):
        return ReservationService(
            reservation_repo=mock_reservation_repo,
            room_repo=mock_room_repo,
            client_repo=mock_client_repo,
            payments_repo=mock_payments_repo,
            uow=mock_unit_of_work,
            task_queuer=mock_task_queuer,
            logger=mock_logger
        )

    def test_create_reservation_success(self, service, mock_reservation_repo, mock_room_repo, mock_client_repo, client_entity, room_entity):
        """Should successfully create a reservation and return a RedirectResultDTO to checkout."""
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=3)
        data = {
            "client_id": 1,
            "room_pk": 1,
            "check_in": checkin,
            "check_out": checkout,
            "observations": "Service test"
        }

        mock_client_repo.get_by_id.return_value = Result.Ok(client_entity)
        mock_room_repo.find_by_id.return_value = Result.Ok(room_entity)
        mock_reservation_repo.has_overlapping_reservation.return_value = Result.Ok(False)
        mock_reservation_repo.fetch_pending.return_value = Result.Ok(None)

        # Mocking the actual save in InitializeReservationUseCase
        res = Reservation.safe_create(
            id=123,
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="Service test",
            amount=Decimal("600.00"),
            status=ReservationStatusEnum.INITIALIZED
        ).unwrap()
        mock_reservation_repo.save.return_value = Result.Ok(res)

        result = service.create_reservation(data)

        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'checkout'
        assert dto.args == (123,)

    def test_create_reservation_invalid_data(self, service):
        """Should return a RedirectResultDTO with error message when input data is invalid."""
        data = {"client_id": "invalid"} # Missing fields, invalid type

        result = service.create_reservation(data)

        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'rooms'
        assert any(m.typ == 'error' for m in dto.messages)

    def test_can_client_create_reservation_true(self, service, mock_reservation_repo):
        """Should return a TemplateRenderResultDTO when the client has no active reservations."""
        mock_reservation_repo.has_active_reservation.return_value = Result.Ok(False)

        result = service.can_client_create_reservation(client_id=1)

        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'reserve.html'

    def test_can_client_create_reservation_false(self, service, mock_reservation_repo):
        """Should return a RedirectResultDTO when the client already has an active reservation."""
        mock_reservation_repo.has_active_reservation.return_value = Result.Ok(True)

        result = service.can_client_create_reservation(client_id=1)

        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'rooms'
        assert any(str(ReservationMessages.ALREADY_HAVE_A_RESERVATION) in m.msg for m in dto.messages)

    def test_can_cancel_reservation_true(self, service, client_entity, room_entity):
        """Should return True if the reservation is in a cancellable state and within the allowed time frame."""
        # Active and far in the future
        res = Reservation.safe_create(
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100"),
            status=ReservationStatusEnum.ACTIVE
        ).unwrap()

        assert service.can_cancel_reservation(res) is True

    def test_can_cancel_reservation_false_status(self, service, client_entity, room_entity):
        """Should return False if the reservation status is not ACTIVE or SCHEDULED."""
        res = Reservation.safe_create(
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100"),
            status=ReservationStatusEnum.FINISHED
        ).unwrap()

        assert service.can_cancel_reservation(res) is False

    def test_fetch_reservation_detail_success(self, service, mock_reservation_repo, client_entity, room_entity):
        """Should successfully fetch reservation details and return a TemplateRenderResultDTO."""
        res = Reservation.safe_create(
            id=1,
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100"),
            status=ReservationStatusEnum.ACTIVE
        ).unwrap()
        mock_reservation_repo.fetch_for_history_detail.return_value = Result.Ok(res)

        result = service.fetch_reservation_detail(client_id=1, reservation_id=1)

        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'cancel_reservation.html'
        assert dto.context['reservation'] == res

    def test_cancel_reservation_success(self, service, mock_reservation_repo, mock_payments_repo, client_entity, room_entity):
        """Should successfully cancel a reservation and return a success RedirectResultDTO."""
        client_entity.id = 1
        res = Reservation.safe_create(
            id=123,
            checkin=date.today() + timedelta(days=10),
            checkout=date.today() + timedelta(days=12),
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100"),
            status=ReservationStatusEnum.SCHEDULED
        ).unwrap()

        mock_reservation_repo.find_by_id.return_value = Result.Ok(res)
        mock_reservation_repo.save.return_value = Result.Ok(res)
        mock_payments_repo.get_by_reservation_id.return_value = Result.Err("No payment")

        result = service.cancel_reservation(reservation_id=123, client_id=1)

        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'reservations_history'
        assert any(m.typ == 'success' for m in dto.messages)
