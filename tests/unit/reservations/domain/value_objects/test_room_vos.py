import pytest
from pydantic import ValidationError
from decimal import Decimal

from reservations.domain.value_objects import (
    RoomNumber,
    RoomClassName,
    AdultsCapacity,
    ChildrenCapacity,
    RoomSize,
    DailyPrice,
    RoomShortDesc,
    RoomLongDesc,
)
from reservations.rules import RoomRules, RoomClassRules


class TestRoomNumber:
    def test_valid_room_numbers(self, validate_vo):
        assert validate_vo(RoomNumber, "101") == "101"
        assert validate_vo(RoomNumber, "101A") == "101A"
        assert validate_vo(RoomNumber, "999Z") == "999Z"

    def test_invalid_room_numbers(self, validate_vo):
        invalid_numbers = [
            "10",       # Too short
            "10000",    # Too long
            "ABC",      # No digits
            "10a",      # Lowercase letter (regex expects uppercase)
            "101AB",    # Too many letters
            "10-",      # Special char
        ]
        for number in invalid_numbers:
            with pytest.raises(ValidationError):
                validate_vo(RoomNumber, number)


class TestRoomClassName:
    def test_valid_names(self, validate_vo):
        assert validate_vo(RoomClassName, "Suite") == "Suite"
        assert validate_vo(RoomClassName, "Deluxe Room") == "Deluxe Room"
        assert validate_vo(RoomClassName, "A" * RoomClassRules.MAX_LEN) == "A" * RoomClassRules.MAX_LEN

    def test_invalid_names(self, validate_vo):
        invalid_names = [
            "",                                 # Empty
            "A" * (RoomClassRules.MAX_LEN + 1), # Too long
            "Suite!",                           # Special char
            " Suite",                           # Starts with space (regex ^\w)
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                validate_vo(RoomClassName, name)


class TestAdultsCapacity:
    def test_valid_capacity(self, validate_vo):
        assert validate_vo(AdultsCapacity, RoomRules.MIN_ADULTS) == RoomRules.MIN_ADULTS
        assert validate_vo(AdultsCapacity, RoomRules.MAX_ADULTS) == RoomRules.MAX_ADULTS

    def test_invalid_capacity(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(AdultsCapacity, RoomRules.MIN_ADULTS - 1)
        with pytest.raises(ValidationError):
            validate_vo(AdultsCapacity, RoomRules.MAX_ADULTS + 1)


class TestChildrenCapacity:
    def test_valid_capacity(self, validate_vo):
        assert validate_vo(ChildrenCapacity, RoomRules.MIN_CHILDREN) == RoomRules.MIN_CHILDREN
        assert validate_vo(ChildrenCapacity, RoomRules.MAX_CHILDREN) == RoomRules.MAX_CHILDREN

    def test_invalid_capacity(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(ChildrenCapacity, RoomRules.MIN_CHILDREN - 1)
        with pytest.raises(ValidationError):
            validate_vo(ChildrenCapacity, RoomRules.MAX_CHILDREN + 1)


class TestRoomSize:
    def test_valid_size(self, validate_vo):
        assert validate_vo(RoomSize, float(RoomRules.MIN_SIZE)) == float(RoomRules.MIN_SIZE)
        assert validate_vo(RoomSize, float(RoomRules.MAX_SIZE)) == float(RoomRules.MAX_SIZE)

    def test_invalid_size(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(RoomSize, float(RoomRules.MIN_SIZE - 0.1))
        with pytest.raises(ValidationError):
            validate_vo(RoomSize, float(RoomRules.MAX_SIZE + 0.1))


class TestDailyPrice:
    def test_valid_price(self, validate_vo):
        min_price = Decimal(RoomRules.MIN_DAILY_PRICE)
        max_price = Decimal(RoomRules.MAX_DAILY_PRICE)
        assert validate_vo(DailyPrice, min_price) == min_price
        assert validate_vo(DailyPrice, max_price) == max_price

    def test_invalid_price(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(DailyPrice, Decimal(RoomRules.MIN_DAILY_PRICE) - Decimal('0.01'))
        with pytest.raises(ValidationError):
            validate_vo(DailyPrice, Decimal(RoomRules.MAX_DAILY_PRICE) + Decimal('0.01'))


class TestRoomShortDesc:
    def test_valid_desc(self, validate_vo):
        desc = "A nice room"
        assert validate_vo(RoomShortDesc, desc) == desc
        assert validate_vo(RoomShortDesc, "a" * RoomRules.SHORT_DESC_MAX_LEN) == "a" * RoomRules.SHORT_DESC_MAX_LEN

    def test_invalid_desc(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(RoomShortDesc, "a" * (RoomRules.SHORT_DESC_MAX_LEN + 1))


class TestRoomLongDesc:
    def test_valid_desc(self, validate_vo):
        desc = "A very nice room with view"
        assert validate_vo(RoomLongDesc, desc) == desc
        assert validate_vo(RoomLongDesc, "a" * RoomRules.LONG_DESC_MAX_LEN) == "a" * RoomRules.LONG_DESC_MAX_LEN

    def test_invalid_desc(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(RoomLongDesc, "a" * (RoomRules.LONG_DESC_MAX_LEN + 1))
