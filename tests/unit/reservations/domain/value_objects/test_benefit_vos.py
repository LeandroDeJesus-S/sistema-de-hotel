import pytest
from pydantic import ValidationError

from reservations.domain.value_objects import (
    BenefitName,
    BenefitShortDesc,
    BenefitIcon,
)
from reservations.rules import BenefitRules


class TestBenefitName:
    def test_valid_names(self, validate_vo):
        assert validate_vo(BenefitName, "WiFi") == "WiFi"
        assert validate_vo(BenefitName, "Air-Conditioning") == "Air-Conditioning"
        assert validate_vo(BenefitName, "Breakfast Included") == "Breakfast Included"

    def test_invalid_names(self, validate_vo):
        invalid_names = [
            "",                                 # Empty
            "A" * (BenefitRules.NAME_MAX_LEN + 1), # Too long
            "WiFi!",                            # Special char not allowed
            "@Home",                            # Special char not allowed
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                validate_vo(BenefitName, name)


class TestBenefitShortDesc:
    def test_valid_desc(self, validate_vo):
        desc = "High speed internet"
        assert validate_vo(BenefitShortDesc, desc) == desc
        assert validate_vo(BenefitShortDesc, "a" * BenefitRules.SHORT_DESC_MAX_LEN) == "a" * BenefitRules.SHORT_DESC_MAX_LEN

    def test_invalid_desc(self, validate_vo):
        invalid_descs = [
            "",                                         # Empty
            "a" * (BenefitRules.SHORT_DESC_MAX_LEN + 1), # Too long
        ]
        for desc in invalid_descs:
            with pytest.raises(ValidationError):
                validate_vo(BenefitShortDesc, desc)


class TestBenefitIcon:
    def test_valid_icon(self, validate_vo):
        icon = "path/to/icon.png"
        assert validate_vo(BenefitIcon, icon) == icon
        assert validate_vo(BenefitIcon, "a" * BenefitRules.ICON_MAX_LEN) == "a" * BenefitRules.ICON_MAX_LEN

    def test_invalid_icon(self, validate_vo):
        with pytest.raises(ValidationError):
            validate_vo(BenefitIcon, "a" * (BenefitRules.ICON_MAX_LEN + 1))
