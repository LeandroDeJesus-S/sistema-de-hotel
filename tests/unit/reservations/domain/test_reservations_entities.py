from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from reservations.domain.entities import Reservation
from reservations.domain.value_objects import Currency, PriceValue
from reservations.feedback_messages import ReserveErrorMessages
from reservations.rules import ReserveRules


class TestReservation:
    """Tests for Reservation entity."""

    def test_reservation_days(self, client_entity, room_entity):
        """Should return the correct number of days."""
        now = datetime.now(tz=timezone.utc)
        checkin = now + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('1000.00') * 100),
        ).unwrap()

        assert reservation.reservation_days().unwrap() == 5

    def test_stayed_days_too_long(self, client_entity, room_entity):
        """Should fail if stay is longer than max days."""
        now = datetime.now(tz=timezone.utc)
        checkin = now
        checkout = checkin + timedelta(days=ReserveRules.MAX_RESERVATION_DAYS + 1)
        res_result = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('100.00') * 100),
        )
        assert res_result.is_err()
        assert str(ReserveErrorMessages.INVALID_STAYED_DAYS) in res_result.unwrap_err().msg

    def test_update_existing_reservation_past_date(self, client_entity, room_entity):
        """Should allow past checkin if reservation already exists."""
        now = datetime.now(tz=timezone.utc)
        checkin = now - timedelta(days=10)
        checkout = checkin + timedelta(days=5)

        # We pass id=1 to simulate existing reservation
        res_result = Reservation.safe_create(
            id=1,
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations='Old res',
            currency=Currency.USD,
            price=int(Decimal('500.00') * 100),
        )
        assert res_result.is_ok()
        assert res_result.unwrap().checkin == checkin

    def test_reservation_str(self, client_entity, room_entity):
        """Should return the correct string representation."""
        now = datetime.now(tz=timezone.utc)
        checkin = now
        checkout = checkin + timedelta(days=3)
        reservation = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations='',
            currency=Currency.USD,
            price=int(Decimal('600.00') * 100),
        ).unwrap()

        assert str(reservation) == f'{checkin} - {checkout}'
