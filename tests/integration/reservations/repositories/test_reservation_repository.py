import pytest
from datetime import date, timedelta
from decimal import Decimal
from reservations.infra.repo import ReservationRepository
from reservations.domain.entities import Reservation
from reservations.domain.value_objects import ReservationStatusEnum
from reservations.models import Reservation as ReservationModel
from ddf import G

@pytest.mark.django_db
class TestReservationRepository:
    @pytest.fixture
    def repo(self):
        return ReservationRepository()

    def test_save_new_reservation(self, repo, client_model_instance, room_model_instance):
        """Should successfully save a new Reservation entity to the database."""
        # Convert models to entities for the repository save method
        from utils.support import model_to_entity
        from clients.domain.entities import Client as ClientEntity
        from reservations.domain.entities import Room as RoomEntity

        client_entity = model_to_entity(client_model_instance, ClientEntity).unwrap()
        room_entity = model_to_entity(room_model_instance, RoomEntity).unwrap()

        checkin = date.today() + timedelta(days=10)
        checkout = checkin + timedelta(days=5)

        reservation_entity = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="Integration test",
            amount=Decimal("1000.00"),
            status=ReservationStatusEnum.INITIALIZED
        ).unwrap()

        result = repo.save(reservation_entity)

        assert result.is_ok()
        saved_res = result.unwrap()
        assert saved_res.id is not None
        assert ReservationModel.objects.filter(id=saved_res.id).exists()

    def test_has_overlapping_reservation(self, repo, reservation_model_instance):
        """Should return True if there is an overlapping reservation for the given room and dates."""
        # reservation_model_instance checkin/checkout are set in conftest.py
        # checkin = date.today() + 10, checkout = checkin + 15

        # Exact overlap
        assert repo.has_overlapping_reservation(
            room_id=reservation_model_instance.room.id,
            check_in=reservation_model_instance.checkin,
            check_out=reservation_model_instance.checkout
        ).unwrap() is False # Wait, conftest sets status='I' (INITIALIZED).
        # has_overlapping_reservation filters by status in [ACTIVE, SCHEDULED].

        # Let's update status to ACTIVE
        reservation_model_instance.status = ReservationStatusEnum.ACTIVE.value
        reservation_model_instance.save()

        assert repo.has_overlapping_reservation(
            room_id=reservation_model_instance.room.id,
            check_in=reservation_model_instance.checkin,
            check_out=reservation_model_instance.checkout
        ).unwrap() is True

    def test_fetch_active_reservations(self, repo, reservation_model_instance):
        """Should return a list of active reservations for a client."""
        reservation_model_instance.status = ReservationStatusEnum.ACTIVE.value
        reservation_model_instance.save()

        result = repo.fetch_active_reservations(reservation_model_instance.client.id)

        assert result.is_ok()
        reservations = result.unwrap()
        assert len(reservations) >= 1
        assert any(r.id == reservation_model_instance.id for r in reservations)

    def test_has_active_reservation(self, repo, reservation_model_instance):
        """Should return True if the client has an active reservation."""
        reservation_model_instance.status = ReservationStatusEnum.ACTIVE.value
        reservation_model_instance.save()

        assert repo.has_active_reservation(reservation_model_instance.client.id, include_scheduled=False).unwrap() is True

    def test_fetch_client_history(self, repo, reservation_model_instance):
        """Should return the full reservation history for a client."""
        result = repo.fetch_client_history(reservation_model_instance.client.id)

        assert result.is_ok()
        history = result.unwrap()
        assert len(history) >= 1
        assert any(r.id == reservation_model_instance.id for r in history)

    def test_fetch_for_history_detail(self, repo, reservation_model_instance):
        """Should return a specific reservation entity for a client and reservation ID."""
        result = repo.fetch_for_history_detail(
            client_id=reservation_model_instance.client.id,
            reservation_id=reservation_model_instance.id
        )

        assert result.is_ok()
        assert result.unwrap().id == reservation_model_instance.id

    def test_find_by_id(self, repo, reservation_model_instance):
        """Should return a Reservation entity when a valid ID is provided."""
        result = repo.find_by_id(reservation_model_instance.id)

        assert result.is_ok()
        assert result.unwrap().id == reservation_model_instance.id

    def test_fetch_pending(self, repo, reservation_model_instance):
        """Should return a pending (INITIALIZED) reservation matching the criteria."""
        # reservation_model_instance is INITIALIZED by default in conftest
        result = repo.fetch_pending(
            client_id=reservation_model_instance.client.id,
            room_id=reservation_model_instance.room.id,
            check_in=reservation_model_instance.checkin,
            check_out=reservation_model_instance.checkout
        )

        assert result.is_ok()
        assert result.unwrap().id == reservation_model_instance.id
