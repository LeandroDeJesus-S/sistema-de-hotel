from datetime import date, timedelta

import pytest
from pydantic import TypeAdapter, ValidationError

import exc
from clients.domain.value_objects import (
    CPF,
    Birthdate,
    Email,
    FirstName,
    LastName,
    Password,
    PhoneNumber,
    Username,
)
from clients.rules import ClientRules


class TestUsername:
    """Test suite for the Username value object."""
    validator = TypeAdapter(Username)

    def test_valid_username(self):
        """Should accept valid usernames."""
        # Arrange
        valid_usernames = ["validUser", "user.name", "user@name", "user_name", "user-name"]

        for username in valid_usernames:
            # Act
            result = self.validator.validate_python(username)
            # Assert
            assert result == username

    def test_username_length_boundaries(self):
        """Should accept usernames within the length boundaries."""
        # Arrange
        min_len_username = "a" * ClientRules.USERNAME_MIN_SIZE
        max_len_username = "a" * ClientRules.USERNAME_MAX_SIZE

        # Act & Assert
        assert self.validator.validate_python(min_len_username) == min_len_username
        assert self.validator.validate_python(max_len_username) == max_len_username

    def test_invalid_username_too_short(self):
        """Should reject usernames that are too short."""
        # Arrange
        invalid_username = "a" * (ClientRules.USERNAME_MIN_SIZE - 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(invalid_username)

    def test_invalid_username_too_long(self):
        """Should reject usernames that are too long."""
        # Arrange
        invalid_username = "a" * (ClientRules.USERNAME_MAX_SIZE + 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(invalid_username)

    def test_invalid_username_characters(self):
        """Should reject usernames with invalid characters."""
        # Arrange
        invalid_usernames = ["user name", "user!name"]

        # Act & Assert
        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                self.validator.validate_python(username)


class TestBirthdate:
    """Test suite for the Birthdate value object."""
    validator = TypeAdapter(Birthdate)

    def test_valid_birthdate(self):
        """Should accept a valid birthdate."""
        # Arrange
        today = date.today()
        # 20 years old
        valid_date = today - timedelta(days=365 * 20 + 5)

        # Act
        result = self.validator.validate_python(valid_date)

        # Assert
        assert result == valid_date

    def test_birthdate_min_age(self):
        """Should accept a birthdate exactly at the minimum age."""
        # Arrange
        today = date.today()
        # Birthday today, MIN_AGE years ago
        valid_date = date(today.year - ClientRules.MIN_AGE, today.month, today.day)

        # Act
        result = self.validator.validate_python(valid_date)

        # Assert
        assert result == valid_date

    def test_birthdate_max_age(self):
        """Should accept a birthdate exactly at the maximum age."""
        # Arrange
        today = date.today()
        # Birthday today, MAX_AGE years ago
        valid_date = date(today.year - ClientRules.MAX_AGE, today.month, today.day)

        # Act
        result = self.validator.validate_python(valid_date)

        # Assert
        assert result == valid_date

    def test_invalid_underage(self):
        """Should reject a birthdate if the user is underage."""
        # Arrange
        today = date.today()
        # Born MIN_AGE years ago but tomorrow, so still underage
        invalid_date = date(today.year - ClientRules.MIN_AGE, today.month, today.day) + timedelta(days=1)

        # Act & Assert
        with pytest.raises(exc.Error):
            self.validator.validate_python(invalid_date)

    def test_invalid_overage(self):
        """Should reject a birthdate if the user is overage."""
        # Arrange
        today = date.today()
        # MAX_AGE + 1 year
        invalid_date = date(today.year - ClientRules.MAX_AGE - 1, today.month, today.day)

        # Act & Assert
        with pytest.raises(exc.Error):
            self.validator.validate_python(invalid_date)

    def test_invalid_future_date(self):
        """Should reject a birthdate in the future."""
        # Arrange
        today = date.today()
        future_date = today + timedelta(days=1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(future_date)


class TestEmail:
    """Test suite for the Email value object."""
    validator = TypeAdapter(Email)

    def test_valid_email(self):
        """Should accept valid email addresses."""
        # Arrange
        valid_emails = ["test@example.com", "user.name@domain.co"]

        # Act & Assert
        for email in valid_emails:
            assert self.validator.validate_python(email) == email

    def test_invalid_email(self):
        """Should reject invalid email addresses."""
        # Arrange
        invalid_emails = ["invalid-email", "@example.com", "user@"]

        # Act & Assert
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                self.validator.validate_python(email)


class TestPhoneNumber:
    """Test suite for the PhoneNumber value object."""
    validator = TypeAdapter(PhoneNumber)

    def test_valid_phone_number(self):
        """Should accept phone numbers within length boundaries."""
        # Arrange
        min_phone = "1" * ClientRules.PHONE_NUMBER_MIN_SIZE
        max_phone = "1" * ClientRules.PHONE_NUMBER_MAX_SIZE

        # Act & Assert
        assert self.validator.validate_python(min_phone) == min_phone
        assert self.validator.validate_python(max_phone) == max_phone

    def test_invalid_phone_too_short(self):
        """Should reject phone numbers that are too short."""
        # Arrange
        invalid_phone = "1" * (ClientRules.PHONE_NUMBER_MIN_SIZE - 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(invalid_phone)

    def test_invalid_phone_too_long(self):
        """Should reject phone numbers that are too long."""
        # Arrange
        invalid_phone = "1" * (ClientRules.PHONE_NUMBER_MAX_SIZE + 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(invalid_phone)


class TestCPF:
    """Test suite for the CPF value object."""
    validator = TypeAdapter(CPF)

    def test_valid_cpf_formatted(self):
        """Should accept formatted CPF numbers."""
        # Arrange
        cpf = "123.456.789-00"

        # Act & Assert
        assert self.validator.validate_python(cpf) == cpf

    def test_valid_cpf_unformatted(self):
        """Should accept unformatted CPF numbers."""
        # Arrange
        cpf = "12345678900"

        # Act & Assert
        assert self.validator.validate_python(cpf) == cpf

    def test_invalid_cpf_pattern(self):
        """Should reject CPFs with invalid patterns."""
        # Arrange
        invalid_cpfs = ["123.456.789.00", "abc.def.ghi-jk"]

        # Act & Assert
        for cpf in invalid_cpfs:
            with pytest.raises(ValidationError):
                self.validator.validate_python(cpf)

    def test_invalid_cpf_length(self):
        """Should reject CPFs that are too short or too long."""
        # Arrange
        too_short = "123"
        too_long = "1" * (ClientRules.CPF_MAX_SIZE + 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(too_short)
        with pytest.raises(ValidationError):
            self.validator.validate_python(too_long)


class TestPassword:
    """Test suite for the Password value object."""
    validator = TypeAdapter(Password)

    def test_valid_password(self):
        """Should accept valid passwords."""
        # Arrange
        pwd = "a" * ClientRules.PASSWORD_MIN_SIZE
        pwd_long = "a" * 50

        # Act & Assert
        assert self.validator.validate_python(pwd) == pwd
        assert self.validator.validate_python(pwd_long) == pwd_long

    def test_invalid_password_too_short(self):
        """Should reject passwords that are too short."""
        # Arrange
        invalid_pwd = "a" * (ClientRules.PASSWORD_MIN_SIZE - 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(invalid_pwd)


class TestFirstName:
    """Test suite for the FirstName value object."""
    validator = TypeAdapter(FirstName)

    def test_valid_first_name(self):
        """Should accept valid first names."""
        # Arrange
        valid_names = ["John", "Ana"]

        # Act & Assert
        for name in valid_names:
            assert self.validator.validate_python(name) == name

    def test_first_name_length_boundaries(self):
        """Should accept first names within length boundaries."""
        # Arrange
        min_name = "a" * ClientRules.MIN_FIRSTNAME_CHARS
        max_name = "a" * ClientRules.MAX_FIRSTNAME_CHARS

        # Act & Assert
        assert self.validator.validate_python(min_name) == min_name
        assert self.validator.validate_python(max_name) == max_name

    def test_invalid_first_name_chars(self):
        """Should reject first names with invalid characters."""
        # Arrange
        invalid_names = ["John1", "John Doe", "John_Doe"]

        # Act & Assert
        for name in invalid_names:
            with pytest.raises(ValidationError):
                self.validator.validate_python(name)

    def test_invalid_first_name_length(self):
        """Should reject first names that are too short or too long."""
        # Arrange
        too_short = "a" * (ClientRules.MIN_FIRSTNAME_CHARS - 1)
        too_long = "a" * (ClientRules.MAX_FIRSTNAME_CHARS + 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(too_short)
        with pytest.raises(ValidationError):
            self.validator.validate_python(too_long)


class TestLastName:
    """Test suite for the LastName value object."""
    validator = TypeAdapter(LastName)

    def test_valid_last_name(self):
        """Should accept valid last names."""
        # Arrange
        valid_names = ["Doe", "Van Der Linde"]

        # Act & Assert
        for name in valid_names:
            assert self.validator.validate_python(name) == name

    def test_last_name_length_boundaries(self):
        """Should accept last names within length boundaries."""
        # Arrange
        min_name = "a" * ClientRules.MIN_SURNAME_CHARS
        max_name = "a" * ClientRules.MAX_SURNAME_CHARS

        # Act & Assert
        assert self.validator.validate_python(min_name) == min_name
        assert self.validator.validate_python(max_name) == max_name

    def test_invalid_last_name_chars(self):
        """Should reject last names with invalid characters."""
        # Arrange
        invalid_names = ["Doe1", "Doe_"]

        # Act & Assert
        for name in invalid_names:
            with pytest.raises(ValidationError):
                self.validator.validate_python(name)

    def test_last_name_strips_whitespace(self):
        """Should strip whitespace from last names."""
        # Arrange
        name_with_spaces = " Doe "

        # Act
        val = self.validator.validate_python(name_with_spaces)

        # Assert
        assert val == "Doe"

    def test_invalid_last_name_length(self):
        """Should reject last names that are too short or too long."""
        # Arrange
        too_short = "a" * (ClientRules.MIN_SURNAME_CHARS - 1)
        too_long = "a" * (ClientRules.MAX_SURNAME_CHARS + 1)

        # Act & Assert
        with pytest.raises(ValidationError):
            self.validator.validate_python(too_short)
        with pytest.raises(ValidationError):
            self.validator.validate_python(too_long)
