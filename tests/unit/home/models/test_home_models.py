"""
Tests for the home app models.
"""

import pytest

from home.models import Hotel


@pytest.mark.django_db
def test_hotel_str_returns_hotel_name(home_models_db_setup):
    """
    Tests if the __str__ method of the Hotel model returns the hotel name.
    """
    # Arrange
    hotel = Hotel.objects.get(pk=1)

    # Act
    result = str(hotel)

    # Assert
    assert result == hotel.name
