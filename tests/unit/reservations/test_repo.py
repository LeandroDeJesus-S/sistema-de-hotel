import pytest

from reservations.infra.repo import ReservationRepository
from reservations.domain.entities import Reservation as ReservationEntity
from reservations.models import Reservation as ReservationModel


@pytest.mark.django_db
class TestReservationRepository:
    def test_find_by_id_found(self, reservation_model: ReservationModel):
        # Arrange
        repo = ReservationRepository()

        # Act
        result = repo.find_by_id(reservation_model.id)

        # Assert
        assert result.error is None
        assert result.value is not None
        assert isinstance(result.value, ReservationEntity)
        assert result.value.id == reservation_model.id
        assert result.value.client.id == reservation_model.client.id
        assert result.value.room.id == reservation_model.room.id

    def test_find_by_id_not_found(self):
        # Arrange
        repo = ReservationRepository()

        # Act
        result = repo.find_by_id(999)

        # Assert
        assert result.error is not None
        assert result.value is None
        assert result.error.msg == "Reservation not found"
