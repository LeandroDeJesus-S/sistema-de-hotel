"""
Tests for the validators.
"""

from string import digits

import pytest
from django.core.exceptions import ValidationError

from clients import validators
from clients.feedback_messages import ContactErrorMessages


@pytest.mark.parametrize(
    'phone',
    [
        *[d * 15 for d in digits],
        '2189654897',
        '0199654897',
        '(21) 965-4897',
        '(21) 9 965-4897',
        '(21) 9 965 4897',
        '(21)9965-4897',
    ],
)
def test_validate_phone_number_with_invalid_phones_raises_error(phone):
    """
    Tests if validate_phone_number raises a ValidationError with an invalid phone.
    """
    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        validators.validate_phone_number(phone)
    assert ContactErrorMessages.INVALID_PHONE in excinfo.value.messages


@pytest.mark.parametrize(
    'phone',
    [
        '21999999999',
        '11988888888',
        '21977777777',
    ],
)
def test_validate_phone_number_with_valid_phones_does_not_raise_error(phone):
    """
    Tests if validate_phone_number does not raise a ValidationError with a valid phone.
    """
    # Act & Assert
    validators.validate_phone_number(phone)


@pytest.mark.parametrize(
    'cpf',
    [
        *[d * 11 for d in digits],
        '12345678910',
        '10987654321',
        '18918918918',
    ],
)
def test_cpf_validator_with_invalid_cpf_raises_error(cpf):
    """
    Tests if CpfValidator raises a ValidationError with an invalid CPF.
    """
    # Arrange
    validator = validators.CpfValidator('test message')

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        validator(cpf)
    assert 'test message' in excinfo.value.messages


def test_cpf_validator_with_valid_cpf_does_not_raise_error(faker):
    """
    Tests if CpfValidator does not raise a ValidationError with a valid CPF.
    """
    # Arrange
    validator = validators.CpfValidator('test message')
    cpf = faker.cpf()

    # Act & Assert
    validator(cpf)
