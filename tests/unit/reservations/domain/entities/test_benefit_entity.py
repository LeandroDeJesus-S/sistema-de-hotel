import pytest
from pydantic import ValidationError

from reservations.domain.entities import Benefit


@pytest.mark.parametrize(
    'name, icon, short_desc',
    [
        ('Wi-Fi', 'wifi-icon.svg', 'Free Wi-Fi'),
        ('Pool', 'pool-icon.svg', 'Outdoor pool'),
    ],
)
def test_benefit_creation_with_valid_data(name, icon, short_desc):
    # When
    benefit = Benefit(name=name, icon=icon, short_desc=short_desc)

    # Then
    assert benefit.name == name
    assert benefit.icon == icon
    assert benefit.short_desc == short_desc


@pytest.mark.parametrize(
    'name, icon, short_desc',
    [
        (
            '',
            'wifi-icon.svg',
            'Free Wi-Fi',
        ),
        (
            'Wi-Fi+',
            'wifi-icon.svg',
            'Free Wi-Fi',
        ),
        (
            'Wi-Fi',
            'a' * 256,
            'Free Wi-Fi',
        ),
        (
            'Wi-Fi',
            'wifi-icon.svg',
            '',
        ),
    ],
)
def test_benefit_creation_with_invalid_data(name, icon, short_desc):
    # When / Then
    with pytest.raises(ValidationError):
        Benefit(name=name, icon=icon, short_desc=short_desc)
