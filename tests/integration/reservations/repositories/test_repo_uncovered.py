import pytest
from datetime import date, datetime, timezone  # Added datetime, timezone
from unittest.mock import Mock
from exc import Result
from reservations.infra.repo import RoomRepository, ReservationRepository
from reservations.models import (
    Reservation as ReservationModel,
    Room as RoomModel,
    Benefit as BenefitModel,
)
from reservations.domain.entities import (
    Room as RoomEntity,
    Reservation as ReservationEntity,
)  # Added these imports


@pytest.mark.django_db
class TestRepoUncovered:
    def test_room_fetch_all_benefits_exception(self, mocker):
        repo = RoomRepository()
        # Mocking the manager's all method
        mock_manager = Mock()
        mock_manager.all.side_effect = Exception('DB Error')
        mocker.patch.object(BenefitModel, 'objects', mock_manager)

        result = repo.fetch_all_benefits()
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch benefits'

    def test_room_save_none_model(self, mocker):
        repo = RoomRepository()
        room_entity = Mock(spec=RoomEntity)
        mocker.patch('reservations.infra.repo.entity_to_model', return_value=Result.Ok(None))

        result = repo.save(room_entity)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to convert room entity to model'

    def test_reservation_save_none_model(self, mocker):
        repo = ReservationRepository()
        res_entity = Mock(spec=ReservationEntity)
        mocker.patch('reservations.infra.repo.entity_to_model', return_value=Result.Ok(None))

        result = repo.save(res_entity)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Failed to convert reservation entity to model'

    def test_has_overlapping_reservation_exception(self, mocker):
        repo = ReservationRepository()
        mock_manager = mocker.Mock()
        mock_manager.filter.side_effect = Exception('DB Error')
        # Ensure we patch where the code looks for it
        mocker.patch.object(repo, '_modelclass', mocker.Mock(objects=mock_manager))

        result = repo.has_overlapping_reservation(
            1, datetime.now(timezone.utc), datetime.now(timezone.utc)
        )
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not check for overlapping reservations'

    def test_fetch_active_reservations_exception(self, mocker):
        repo = ReservationRepository()
        mock_manager = mocker.Mock()
        mock_manager.filter.side_effect = Exception('DB Error')
        mocker.patch.object(repo, '_modelclass', mocker.Mock(objects=mock_manager))

        result = repo.fetch_active_reservations(1)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch active reservations'

    def test_fetch_for_history_detail_conversion_error(self, mocker):
        repo = ReservationRepository()
        mock_manager = mocker.Mock()
        mock_manager.filter.return_value.first.return_value = mocker.Mock()
        repo._modelclass = mocker.Mock(objects=mock_manager)

        mocker.patch(
            'reservations.infra.repo.model_to_entity',
            return_value=Result.Err('Conversion error'),
        )

        result = repo.fetch_for_history_detail(1, 1)
        # It just returns the result of model_to_entity
        assert result.is_err()
        assert result.unwrap_err().msg == 'Conversion error'

    def test_room_fetch_all_with_benefits_conversion_error(self, mocker):
        repo = RoomRepository()
        mock_room = Mock()
        mock_benefit = Mock()
        mock_room.benefits.all.return_value = [mock_benefit]

        # Mock QuerySet chain
        mock_qs = mocker.Mock()
        mock_qs.select_related.return_value = mock_qs
        mock_qs.all.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.order_by.return_value = [mock_room]

        mocker.patch.object(RoomModel, 'objects', mock_qs)

        mocker.patch('reservations.infra.repo.model_to_entity', return_value=Result.Ok(Mock()))
        mocker.patch(
            'reservations.infra.repo.models_to_entities',
            side_effect=[
                Result.Ok([]),  # For prices.all()
                Result.Err('Benefit Error'),  # For benefits.all()
            ],
        )

        result = repo.fetch_all(with_benefits=True)
        assert result.is_err()
        assert result.unwrap_err().msg == 'Could not fetch benefits'

    def test_has_active_reservation_false(self, mocker):
        repo = ReservationRepository()
        mocker.patch.object(
            ReservationModel.objects, 'filter', return_value=mocker.Mock(exists=lambda: False)
        )

        result = repo.has_active_reservation(1, False)
        assert result.is_ok()
        assert result.unwrap() is False

    def test_from_room_success(self, mocker):
        repo = ReservationRepository()
        mock_res = Mock()
        mocker.patch.object(
            ReservationModel.objects,
            'filter',
            return_value=mocker.Mock(count=lambda: 1, __iter__=lambda x: iter([mock_res])),
        )
        mocker.patch(
            'reservations.infra.repo.models_to_entities', return_value=Result.Ok([Mock()])
        )

        result = repo.from_room(1)
        assert result.is_ok()
        assert len(result.unwrap()) == 1

    def test_from_room_occupied_only(self, mocker):
        repo = ReservationRepository()
        mock_res = Mock()
        mock_filter = mocker.patch.object(
            ReservationModel.objects,
            'filter',
            return_value=mocker.Mock(count=lambda: 1, __iter__=lambda x: iter([mock_res])),
        )
        mocker.patch(
            'reservations.infra.repo.models_to_entities', return_value=Result.Ok([Mock()])
        )

        result = repo.from_room(1, occuped_only=True)
        assert result.is_ok()
        # Verify filter call arguments
        # It's hard to check exact kwargs with simple patch, but we trust logic.
        # To be sure, we can check if it called with status__in
        args, kwargs = mock_filter.call_args
        assert 'status__in' in kwargs
        assert kwargs['status__in'] == ['A', 'S']

    def test_from_room_no_reservations(self, mocker):
        repo = ReservationRepository()
        mock_manager = mocker.Mock()
        mock_manager.filter.return_value = mocker.Mock(count=lambda: 0)
        repo._modelclass = mocker.Mock(objects=mock_manager)

        result = repo.from_room(999)
        assert result.is_err()
        assert result.unwrap_err().msg == 'No reservations found'
