import pytest

from exc import Error
from reservations.domain.entities import Reservation as ReservationEntity
from reservations.infra.repo import ReservationRepository
from reservations.models import Reservation as ReservationModel


@pytest.mark.django_db
class TestReservationRepository:
    def test_find_by_id_found(self, reservation_model: ReservationModel):
        # Arrange
        repo = ReservationRepository()

        # Act
        result = repo.find_by_id(reservation_model.id)

        # Assert
        assert not result.is_err()
        assert isinstance(result.unwrap(), ReservationEntity)
        assert result.unwrap().id == reservation_model.id
        assert result.unwrap().client.id == reservation_model.client.id
        assert result.unwrap().room.id == reservation_model.room.id

    def test_find_by_id_not_found(self):
        # Arrange
        repo = ReservationRepository()

        # Act
        result = repo.find_by_id(999)

        # Assert
        assert result.is_err()
        assert isinstance(result.unwrap_err(), Error)
