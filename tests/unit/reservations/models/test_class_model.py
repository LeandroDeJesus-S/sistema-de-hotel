"""
Tests for the Class model.
"""

import pytest
from django.core.exceptions import ValidationError

from reservations.feedback_messages import ClasseErrorMessages
from reservations.models import Class


@pytest.mark.django_db
def test_class_creation_with_valid_name(room_class_model):
    """
    Tests if a class is created correctly with a valid name.
    """
    # Assert
    assert Class.objects.filter(pk=room_class_model.pk).exists()


@pytest.mark.parametrize(
    'name',
    [
        'class #1',
        'class-1',
        'class @2',
        ' ',
    ],
)
@pytest.mark.django_db
def test_class_creation_with_invalid_name(name, room_class_model):
    """
    Tests if a class is not created if the name is invalid.
    """
    # Arrange
    room_class_model.name = name

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        room_class_model.full_clean()
    assert ClasseErrorMessages.INVALID_NAME in excinfo.value.messages
