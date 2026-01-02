import pytest
from datetime import date
from pydantic import ValidationError

from reservations.domain.value_objects import (
    ReservationStatusEnum,
    ReservationObservations,
    CheckInOut,
)
from reservations.rules import ReserveRules


class TestReservationStatusEnum:
    def test_valid_statuses(self, validate_vo):
        for status in ReservationStatusEnum:
            assert validate_vo(ReservationStatusEnum, status.value) == status

    def test_invalid_status(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(ReservationStatusEnum, "X")


class TestReservationObservations:
    def test_valid_observations(self, validate_vo):
        obs = "Late checkin request"
        assert validate_vo(ReservationObservations, obs) == obs
        assert validate_vo(ReservationObservations, "") == ""
        # Assuming regex allows spaces and word chars.
        # rules.ReserveRules.OBSERVATIONS_PATTERN = r'[\w\s]*'

    def test_invalid_observations(self, validate_vo):
        invalid_obs = [
            "a" * (ReserveRules.OBSERVATIONS_MAX_LEN + 1), # Too long
            "Bad char @",                                  # Special char if not allowed (checking regex)
        ]
        # Regex is r'[\w\s]*', so @ should fail
        for obs in invalid_obs:
            with pytest.raises(ValidationError):
                validate_vo(ReservationObservations, obs)


class TestCheckInOut:
    def test_valid_date_obj(self, validate_vo):
        d = date(2023, 1, 1)
        assert validate_vo(CheckInOut, d) == d

    def test_valid_date_str(self, validate_vo):
        d_str = "2023-01-01"
        expected = date(2023, 1, 1)
        assert validate_vo(CheckInOut, d_str) == expected

    def test_invalid_date_str(self, validate_vo):
        invalid_dates = [
            "01/01/2023", # Wrong format
            "2023-13-01", # Invalid month
            "not-a-date",
        ]
        for d in invalid_dates:
            with pytest.raises(ValueError): # convert_date raises ValueError wrapped in Pydantic validation error?
                 # Actually BeforeValidator might raise ValueError which Pydantic catches or propagates
                 # let's check validation error message if needed, but ValidationError is expected
                 # However, my validator raises ValueError explicitly with message.
                 # Pydantic wraps it in ValidationError.
                 validate_vo(CheckInOut, d)
