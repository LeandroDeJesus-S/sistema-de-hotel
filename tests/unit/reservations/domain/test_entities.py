from datetime import date, timedelta
from decimal import Decimal

from reservations.domain.entities import Reservation
from reservations.feedback_messages import ReserveErrorMessages
from reservations.rules import ReserveRules


class TestReservation:
    """Tests for Reservation entity."""

    def test_reservation_days(self, client_entity, room_entity):
        """Should return the correct number of days."""
        checkin = date.today()
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("1000.00")
        ).unwrap()

        assert reservation.reservation_days().unwrap() == 5

    def test_create_valid_reservation(self, client_entity, room_entity):
        """Should create a valid reservation."""
        checkin = date.today()
        checkout = checkin + timedelta(days=3)
        res_result = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="Late checkin",
            amount=Decimal("600.00")
        )
        assert res_result.is_ok()
        assert res_result.unwrap().checkin == checkin
        assert res_result.unwrap().checkout == checkout

    def test_checkin_in_past(self, client_entity, room_entity):
        """Should fail if checkin is in the past for new reservation."""
        checkin = date.today() - timedelta(days=1)
        checkout = checkin + timedelta(days=3)
        res_result = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100.00")
        )
        assert res_result.is_err()
        assert str(ReserveErrorMessages.INVALID_CHECKIN_DATE) in res_result.unwrap_err().msg

    def test_checkin_too_far(self, client_entity, room_entity):
        """Should fail if checkin is beyond anticipation limit."""
        limit = ReserveRules.checkin_anticipation_offset()
        checkin = limit + timedelta(days=1)
        checkout = checkin + timedelta(days=3)
        res_result = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100.00")
        )
        assert res_result.is_err()
        assert str(ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION) in res_result.unwrap_err().msg

    def test_checkin_after_checkout(self, client_entity, room_entity):
        """Should fail if checkin is after checkout."""
        checkin = date.today() + timedelta(days=5)
        checkout = date.today() + timedelta(days=3)
        res_result = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100.00")
        )
        assert res_result.is_err()
        assert str(ReserveErrorMessages.INVALID_CHECKIN_DATE) in res_result.unwrap_err().msg

    def test_stayed_days_too_short(self, client_entity, room_entity):
        """Should fail if stay is shorter than min days."""
        checkin = date.today()
        checkout = checkin  # 0 days, assuming MIN is > 0
        res_result = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100.00")
        )
        assert res_result.is_err()
        assert str(ReserveErrorMessages.INVALID_STAYED_DAYS) in res_result.unwrap_err().msg

    def test_stayed_days_too_long(self, client_entity, room_entity):
        """Should fail if stay is longer than max days."""
        checkin = date.today()
        checkout = checkin + timedelta(days=ReserveRules.MAX_RESERVATION_DAYS + 1)
        res_result = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("100.00")
        )
        assert res_result.is_err()
        assert str(ReserveErrorMessages.INVALID_STAYED_DAYS) in res_result.unwrap_err().msg

    def test_update_existing_reservation_past_date(self, client_entity, room_entity):
        """Should allow past checkin if reservation already exists."""
        checkin = date.today() - timedelta(days=10)
        checkout = checkin + timedelta(days=5)

        # We pass id=1 to simulate existing reservation
        res_result = Reservation.safe_create(
            id=1,
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="Old res",
            amount=Decimal("500.00")
        )
        assert res_result.is_ok()
        assert res_result.unwrap().checkin == checkin

    def test_reservation_str(self, client_entity, room_entity):
        """Should return the correct string representation."""
        checkin = date.today()
        checkout = checkin + timedelta(days=3)
        reservation = Reservation.safe_create(
            checkin=checkin,
            checkout=checkout,
            client=client_entity,
            room=room_entity,
            observations="",
            amount=Decimal("600.00")
        ).unwrap()

        assert str(reservation) == f"{checkin} - {checkout}"
