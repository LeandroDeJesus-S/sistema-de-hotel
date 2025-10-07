"""
Tests for the reservations validators.
"""

from datetime import date

from exc import Error
from reservations import validators


def test_convert_date_with_valid_date():
    """
    Tests if convert_date returns the correct date with a valid date string.
    """
    # Arrange
    str_date = '2024-02-01'

    # Act
    result, _ = validators.convert_date(str_date)

    # Assert
    assert result == date(2024, 2, 1)


def test_convert_date_with_invalid_date_format():
    """
    Tests if convert_date returns the date 1-1-1 when an invalid date format is passed.
    """
    # Arrange
    str_date = '01022024'

    # Act
    result, err = validators.convert_date(str_date)

    # Assert
    assert result is None and isinstance(err, Error)
