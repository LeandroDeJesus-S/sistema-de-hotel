"""
Tests for the payment custom tags.
"""


import pytest

from payments.templatetags import payment_customtags as tags


def test_money_tag_with_valid_string():
    """
    Tests if the money tag returns a valid format when given a valid numeric string.
    """
    # Act
    result = tags.money('20.255')

    # Assert
    assert result == 'R$20.25'


def test_money_tag_raises_type_error_for_invalid_type():
    """
    Tests if a TypeError is raised if the value is not a str, Decimal, or float.
    """
    # Act & Assert
    with pytest.raises(TypeError):
        tags.money([10])


def test_money_tag_raises_value_error_for_unconvertible_string():
    """
    Tests if a ValueError is raised if the value is a string that cannot be converted to a float.
    """
    # Act & Assert
    with pytest.raises(ValueError):
        tags.money('10-5')
