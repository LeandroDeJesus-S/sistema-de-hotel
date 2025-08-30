"""
Tests for the Class model.
"""
import pytest
from django.core.exceptions import ValidationError

from reservations.models import Class
from utils.supportmodels import ClasseErrorMessages


@pytest.mark.django_db
def test_class_creation_with_valid_name():
    """
    Tests if a class is created correctly with a valid name.
    """
    # Arrange
    name = 'The best class'
    classe = Class(name=name)

    # Act
    classe.full_clean()
    classe.save()

    # Assert
    assert Class.objects.filter(pk=classe.pk).exists()


@pytest.mark.parametrize(
    "name",
    [
        'class #1',
        'class-1',
        'class @2',
        ' ',
    ]
)
@pytest.mark.django_db
def test_class_creation_with_invalid_name(name):
    """
    Tests if a class is not created if the name is invalid.
    """
    # Arrange
    classe = Class(name=name)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        classe.full_clean()
    assert ClasseErrorMessages.INVALID_NAME in excinfo.value.messages
