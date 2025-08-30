"""
Tests for the home app models.
"""
import pytest

from home.models import Contact, Hotel


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


@pytest.mark.django_db
def test_contact_str_returns_model_name_and_id(home_models_db_setup):
    """
    Tests if the __str__ method of the Contact model returns the model name and id.
    """
    # Arrange
    contact = Contact.objects.get(pk=1)

    # Act
    result = str(contact)

    # Assert
    assert result == "Contact 1"
