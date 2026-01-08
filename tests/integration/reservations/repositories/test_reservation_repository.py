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
            observations='Integration test',
            amount=Decimal('1000.00'),
            status=ReservationStatusEnum.INITIALIZED,
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
        assert (
            repo.has_overlapping_reservation(
                room_id=reservation_model_instance.room.id,
                check_in=reservation_model_instance.checkin,
                check_out=reservation_model_instance.checkout,
            ).unwrap()
            is False
        )  # Wait, conftest sets status='I' (INITIALIZED).
        # has_overlapping_reservation filters by status in [ACTIVE, SCHEDULED].

        # Let's update status to ACTIVE
        reservation_model_instance.status = ReservationStatusEnum.ACTIVE.value
        reservation_model_instance.save()

        assert (
            repo.has_overlapping_reservation(
                room_id=reservation_model_instance.room.id,
                check_in=reservation_model_instance.checkin,
                check_out=reservation_model_instance.checkout,
            ).unwrap()
            is True
        )

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

        assert (
            repo.has_active_reservation(
                reservation_model_instance.client.id, include_scheduled=False
            ).unwrap()
            is True
        )

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
            reservation_id=reservation_model_instance.id,
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
            check_out=reservation_model_instance.checkout,
        )

        assert result.is_ok()
        assert result.unwrap().id == reservation_model_instance.id

    def test_fetch_active_reservations_include_scheduled(
        self, repo, reservation_model_instance
    ):
        """Should return scheduled reservations when include_scheduled is True."""
        reservation_model_instance.status = ReservationStatusEnum.SCHEDULED.value
        reservation_model_instance.save()

        result = repo.fetch_active_reservations(
            reservation_model_instance.client.id, include_scheduled=True
        )

        assert result.is_ok()
        reservations = result.unwrap()
        assert any(r.id == reservation_model_instance.id for r in reservations)

    def test_has_active_reservation_include_scheduled(self, repo, reservation_model_instance):
        """Should return True for scheduled reservations when include_scheduled is True."""
        reservation_model_instance.status = ReservationStatusEnum.SCHEDULED.value
        reservation_model_instance.save()

        assert (
            repo.has_active_reservation(
                reservation_model_instance.client.id, include_scheduled=True
            ).unwrap()
            is True
        )

    def test_save_conversion_error(
        self, repo, client_model_instance, room_model_instance, mocker
    ):
        from utils.support import model_to_entity
        from clients.domain.entities import Client as ClientEntity
        from reservations.domain.entities import Room as RoomEntity
        from exc import Result

        client_entity = model_to_entity(client_model_instance, ClientEntity).unwrap()
        room_entity = model_to_entity(room_model_instance, RoomEntity).unwrap()
        reservation_entity = Reservation.safe_create(
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations='',
            amount=Decimal('100'),
            status='I',
        ).unwrap()

        mocker.patch(
            'reservations.infra.repo.entity_to_model',
            return_value=Result.Err('Conversion error'),
        )
        result = repo.save(reservation_entity)
        assert result.is_err()

    def test_save_validation_error(
        self, repo, client_model_instance, room_model_instance, mocker
    ):
        from utils.support import model_to_entity
        from clients.domain.entities import Client as ClientEntity
        from reservations.domain.entities import Room as RoomEntity
        from exc import Result
        from django.core.exceptions import ValidationError

        client_entity = model_to_entity(client_model_instance, ClientEntity).unwrap()
        room_entity = model_to_entity(room_model_instance, RoomEntity).unwrap()
        reservation_entity = Reservation.safe_create(
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations='',
            amount=Decimal('100'),
            status='I',
        ).unwrap()

        mock_model = mocker.Mock()
        mock_model.full_clean.side_effect = ValidationError('Invalid')
        mocker.patch(
            'reservations.infra.repo.entity_to_model', return_value=Result.Ok(mock_model)
        )

        result = repo.save(reservation_entity)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Invalid reservation'

    def test_save_db_error(self, repo, client_model_instance, room_model_instance, mocker):
        from utils.support import model_to_entity
        from clients.domain.entities import Client as ClientEntity
        from reservations.domain.entities import Room as RoomEntity
        from exc import Result

        client_entity = model_to_entity(client_model_instance, ClientEntity).unwrap()
        room_entity = model_to_entity(room_model_instance, RoomEntity).unwrap()
        reservation_entity = Reservation.safe_create(
            checkin=date.today(),
            checkout=date.today() + timedelta(days=1),
            client=client_entity,
            room=room_entity,
            observations='',
            amount=Decimal('100'),
            status='I',
        ).unwrap()

        mock_model = mocker.Mock()
        mock_model.save.side_effect = Exception('DB Error')
        mocker.patch(
            'reservations.infra.repo.entity_to_model', return_value=Result.Ok(mock_model)
        )

        result = repo.save(reservation_entity)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not save reservation'

    def test_has_overlapping_reservation_exception(self, repo, mocker):
        mocker.patch.object(
            ReservationModel.objects, 'filter', side_effect=Exception('DB Error')
        )
        result = repo.has_overlapping_reservation(1, date.today(), date.today())
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not check for overlapping reservations'

    def test_fetch_active_reservations_exception(self, repo, mocker):
        mocker.patch.object(
            ReservationModel.objects, 'filter', side_effect=Exception('DB Error')
        )
        result = repo.fetch_active_reservations(1)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch active reservations'

    def test_has_active_reservation_exception(self, repo, mocker):
        mocker.patch.object(
            ReservationModel.objects, 'filter', side_effect=Exception('DB Error')
        )
        result = repo.has_active_reservation(1, False)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not check for active reservation'

    def test_fetch_client_history_exception(self, repo, mocker):
        mocker.patch.object(
            ReservationModel.objects, 'filter', side_effect=Exception('DB Error')
        )
        result = repo.fetch_client_history(1)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch client history'

    def test_fetch_for_history_detail_not_found(self, repo):
        result = repo.fetch_for_history_detail(999, 999)
        assert result.is_err()
        assert 'Reservation not found' in result.unwrap_err().msg

    def test_find_by_id_not_found(self, repo):
        result = repo.find_by_id(999)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Reservation not found'

    def test_fetch_pending_not_found(self, repo):
        result = repo.fetch_pending(999, 999, date.today(), date.today())
        assert result.is_err()
        assert result.unwrap_err().msg == 'Reservation not found'

    def test_from_room_no_reservations(self, repo):
        result = repo.from_room(999)
        assert result.is_err()
        assert result.unwrap_err().msg == 'No reservations found'

    def test_fetch_all_active(self, repo, reservation_model_instance):
        """Should return all reservations with ACTIVE status."""
        # Ensure our test reservation is ACTIVE
        reservation_model_instance.status = ReservationStatusEnum.ACTIVE.value
        reservation_model_instance.save()

        # Create another ACTIVE reservation for the same client
        active_reservation = G(
            ReservationModel,
            client=reservation_model_instance.client,
            room=reservation_model_instance.room,
            status=ReservationStatusEnum.ACTIVE.value,
            checkin=date.today() + timedelta(days=20),
            checkout=date.today() + timedelta(days=25),
            amount=Decimal('500.00'),
        )

        # Create a non-ACTIVE reservation that should NOT be returned
        G(
            ReservationModel,
            client=reservation_model_instance.client,
            room=reservation_model_instance.room,
            status=ReservationStatusEnum.INITIALIZED.value,  # Not ACTIVE
            checkin=date.today() + timedelta(days=30),
            checkout=date.today() + timedelta(days=35),
            amount=Decimal('300.00'),
        )

        result = repo.fetch_all_active()

        assert result.is_ok()
        active_reservations = result.unwrap()

        # Should return exactly 2 ACTIVE reservations
        assert len(active_reservations) == 2

        # Verify both our test reservations are included
        reservation_ids = [r.id for r in active_reservations]
        assert reservation_model_instance.id in reservation_ids
        assert active_reservation.id in reservation_ids

        # Verify all returned reservations have ACTIVE status
        for reservation in active_reservations:
            assert reservation.status == ReservationStatusEnum.ACTIVE

    def test_fetch_all_active_exception(self, repo, mocker):
        """Should handle database exceptions gracefully."""
        mocker.patch.object(
            ReservationModel.objects, 'filter', side_effect=Exception('DB Error')
        )
        result = repo.fetch_all_active()
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch all active reservations'
