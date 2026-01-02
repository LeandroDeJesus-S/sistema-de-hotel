"""
Tests for the Benefit model.
"""

import pytest
from django.core.exceptions import ValidationError

from reservations.feedback_messages import BenefitErrorMessages


@pytest.mark.django_db
def test_icon_larger_than_64x64_raises_validation_error(benefit_model):
    """
    Tests if an icon larger than 64x64 raises a ValidationError.
    """
    # Arrange
    benefit_model.icon = 'test/room_test.jpg'

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        benefit_model.full_clean()
    assert BenefitErrorMessages.INVALID_ICON_SIZE in excinfo.value.messages


@pytest.mark.django_db
def test_missing_name_raises_validation_error(benefit_model):
    """
    Tests if a missing name raises a ValidationError.
    """
    # Arrange
    benefit_model.name = ''

    # Act & Assert
    with pytest.raises(ValidationError):
        benefit_model.full_clean()


@pytest.mark.django_db
def test_missing_short_desc_raises_validation_error(benefit_model):
    """
    Tests if a missing short_desc raises a ValidationError.
    """
    # Arrange
    benefit_model.short_desc = ''

    # Act & Assert
    with pytest.raises(ValidationError):
        benefit_model.full_clean()
