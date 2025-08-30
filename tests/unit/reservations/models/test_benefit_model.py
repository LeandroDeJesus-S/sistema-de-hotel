"""
Tests for the Benefit model.
"""
import pytest
from django.core.exceptions import ValidationError

from reservations.models import Benefit
from utils.supportmodels import BenefitErrorMessages





@pytest.mark.django_db
def test_benefit_creation_with_valid_data(valid_benefit_data):
    """
    Tests if a benefit is saved to the database if all
    the data sent is valid.
    """
    # Arrange
    benefit = Benefit(**valid_benefit_data)

    # Act
    benefit.full_clean()
    benefit.save()

    # Assert
    assert Benefit.objects.filter(pk=benefit.pk).exists()


@pytest.mark.django_db
def test_icon_larger_than_64x64_raises_validation_error(valid_benefit_data):
    """
    Tests if an icon larger than 64x64 raises a ValidationError.
    """
    # Arrange
    valid_benefit_data['icon'] = 'test/room_test.jpg'
    benefit = Benefit(**valid_benefit_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        benefit.full_clean()
    assert BenefitErrorMessages.INVALID_ICON_SIZE in excinfo.value.messages


@pytest.mark.django_db
def test_missing_name_raises_validation_error(valid_benefit_data):
    """
    Tests if a missing name raises a ValidationError.
    """
    # Arrange
    valid_benefit_data['name'] = ''
    benefit = Benefit(**valid_benefit_data)

    # Act & Assert
    with pytest.raises(ValidationError):
        benefit.full_clean()


@pytest.mark.django_db
def test_missing_short_desc_raises_validation_error(valid_benefit_data):
    """
    Tests if a missing short_desc raises a ValidationError.
    """
    # Arrange
    valid_benefit_data['short_desc'] = ''
    benefit = Benefit(**valid_benefit_data)

    # Act & Assert
    with pytest.raises(ValidationError):
        benefit.full_clean()
