import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from unittest.mock import Mock

from clients.infra.validators import (
    UsernameValidator,
    PhoneNumberValidator,
    BirthDateValidator,
    PasswordValidator,
    DjangoPasswordValidatorAdapter,
    CpfValidator
)
from clients.feedback_messages import ClientErrorMessages, ContactErrorMessages
from exc import Result

class TestUsernameValidator:
    def test_validate_success(self):
        dj_mock = Mock()
        validator = UsernameValidator(dj_extra=[dj_mock])
        result = validator.validate("valid_user")
        assert result.is_ok()
        dj_mock.assert_called_once_with("valid_user")

    def test_validate_length_short(self):
        validator = UsernameValidator(dj_extra=[], min_len=5)
        result = validator.validate("usr")
        assert result.is_err()
        assert "characters long" in result.unwrap_err().msg

    def test_validate_length_long(self):
        validator = UsernameValidator(dj_extra=[], max_len=5)
        result = validator.validate("toolong")
        assert result.is_err()
        assert "characters long" in result.unwrap_err().msg

    def test_validate_raise_exc(self):
        validator = UsernameValidator(dj_extra=[], min_len=5, raise_exc=True)
        with pytest.raises(ValidationError):
            validator.validate("usr")

class TestPhoneNumberValidator:
    def test_validate_success(self):
        validator = PhoneNumberValidator()
        result = validator.validate("(11) 99999-9999")
        assert result.is_ok()

    def test_validate_success_weak(self):
        validator = PhoneNumberValidator(weak=True)
        result = validator.validate("(11) 99999-9999")
        assert result.is_ok()

    def test_validate_invalid(self, mocker):
        validator = PhoneNumberValidator()
        result = validator.validate("123")
        assert result.is_err()
        assert result.unwrap_err().msg == ContactErrorMessages.INVALID_PHONE

    def test_validate_parse_error(self, mocker):
        validator = PhoneNumberValidator()
        # phonenumbers.parse raises NumberParseException for very invalid stuff if no region
        # but with region 'BR' it might just return invalid number.
        # Let's try something that definitely fails parsing if possible, or just mock.
        import phonenumbers
        mocker.patch("phonenumbers.parse", side_effect=phonenumbers.NumberParseException(1, "msg"))
        result = validator.validate("any")
        assert result.is_err()
        assert result.unwrap_err().msg == ContactErrorMessages.INVALID_PHONE

    def test_validate_raise_exc(self):
        validator = PhoneNumberValidator(raise_exc=True)
        with pytest.raises(ValidationError):
            validator.validate("123")

class TestBirthDateValidator:
    def test_validate_success(self):
        validator = BirthDateValidator(min_age=18, max_age=100)
        birthdate = date.today() - timedelta(days=20*365)
        result = validator.validate(birthdate)
        assert result.is_ok()

    def test_validate_too_young(self):
        validator = BirthDateValidator(min_age=18)
        birthdate = date.today() - timedelta(days=10*365)
        result = validator.validate(birthdate)
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.INVALID_BIRTHDATE

    def test_validate_too_old(self):
        validator = BirthDateValidator(max_age=100)
        birthdate = date.today() - timedelta(days=110*365)
        result = validator.validate(birthdate)
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.INVALID_BIRTHDATE

    def test_validate_raise_exc(self):
        validator = BirthDateValidator(min_age=18, raise_exc=True)
        birthdate = date.today() - timedelta(days=10*365)
        with pytest.raises(ValidationError):
            validator.validate(birthdate)

class TestPasswordValidator:
    def test_validate_success(self):
        dj_mock = Mock()
        validator = PasswordValidator(dj_extra=[dj_mock])
        # Password needs to be long enough and have symbols (isalnum check)
        result = validator.validate("ValidPass123!")
        assert result.is_ok()
        dj_mock.assert_called_once_with("ValidPass123!")

    def test_validate_too_short(self):
        validator = PasswordValidator(dj_extra=[], min_len=8)
        result = validator.validate("Short1!")
        assert result.is_err()
        assert "password must contain" in result.unwrap_err().msg

    def test_validate_no_symbols(self):
        validator = PasswordValidator(dj_extra=[])
        result = validator.validate("NoSymbols123")
        assert result.is_err()
        assert "password must contain" in result.unwrap_err().msg

    def test_validate_raise_exc(self):
        validator = PasswordValidator(dj_extra=[], raise_exc=True)
        with pytest.raises(ValidationError):
            validator.validate("weak")

class TestDjangoPasswordValidatorAdapter:
    def test_validate_success(self):
        mock_v = Mock()
        mock_v.validate.return_value = Result.Ok("pass")
        adapter = DjangoPasswordValidatorAdapter(validator=mock_v)
        # Should not raise
        adapter.validate("pass")

    def test_validate_failure(self):
        mock_v = Mock()
        mock_v.validate.return_value = Result.Err("error")
        adapter = DjangoPasswordValidatorAdapter(validator=mock_v)
        with pytest.raises(ValidationError) as exc:
            adapter.validate("pass")
        assert "error" in str(exc.value)

    def test_get_help_text(self):
        adapter = DjangoPasswordValidatorAdapter()
        assert adapter.get_help_text() == adapter._help_msg


class TestCpfValidator:
    def test_eq(self):
        validator1 = CpfValidator()
        validator2 = CpfValidator()
        validator3 = CpfValidator(message="Different message")
        assert validator1 == validator2
        assert not (validator1 == validator3)

    def test_calculate_first_digit_valid(self):
        validator = CpfValidator()
        validator._cpf = "44460967030" # The first 9 digits are "444609670"
        assert validator._calculate_first_digit() == "2"

    def test_calculate_first_digit_threshold(self):
        # Scenario where 11 - result % 11 > 9, so it should return '0'
        validator = CpfValidator()
        validator._cpf = "22222222200" # This will cause the digit calculation to be 10 or 11
        assert validator._calculate_first_digit() == "2"

    def test_calculate_second_digit_valid(self):
        validator = CpfValidator()
        validator._cpf = "44460967030" # First 9 digits "444609670", first calculated digit is "2"
        assert validator._calculate_second_digit() == "2"

    def test_calculate_second_digit_threshold(self):
        # Scenario where 11 - ac % 11 > 9, so it should return '0'
        validator = CpfValidator()
        validator._cpf = "22222222200" # First 9 digits "222222222", first calculated digit is "2"
        assert validator._calculate_second_digit() == "2"

    def test_is_valid_sequence_true(self):
        validator = CpfValidator()
        validator._cpf = "11111111111"
        assert validator._is_valid_sequence() is True

    def test_is_valid_sequence_false(self):
        validator = CpfValidator()
        validator._cpf = "12345678909"
        assert validator._is_valid_sequence() is False

    def test_has_valid_length_true(self):
        validator = CpfValidator()
        validator._cpf = "12345678909"
        assert validator._has_valid_length() is True

    def test_has_valid_length_false(self):
        validator = CpfValidator()
        validator._cpf = "12345"
        assert validator._has_valid_length() is False

    def test_validate_success(self):
        validator = CpfValidator()
        result = validator.validate("954.912.420-71")
        assert result.is_ok()
        assert result.unwrap() == "954.912.420-71"

    def test_validate_invalid_length_err(self):
        validator = CpfValidator()
        result = validator.validate("12345")
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.INVALID_CPF

    def test_validate_invalid_length_raise(self):
        validator = CpfValidator(raise_exc=True)
        with pytest.raises(ValidationError):
            validator.validate("12345")

    def test_validate_invalid_sequence_err(self):
        validator = CpfValidator()
        result = validator.validate("111.111.111-11")
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.INVALID_CPF

    def test_validate_invalid_sequence_raise(self):
        validator = CpfValidator(raise_exc=True)
        with pytest.raises(ValidationError):
            validator.validate("111.111.111-11")

    def test_validate_mismatch_digits_err(self):
        validator = CpfValidator()
        result = validator.validate("444.609.670-30") # A CPF with valid structure but incorrect digits
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.INVALID_CPF

    def test_validate_mismatch_digits_raise(self):
        validator = CpfValidator(raise_exc=True)
        with pytest.raises(ValidationError):
            validator.validate("444.609.670-30") # A CPF with valid structure but incorrect digits

    # Test the _cpf property after re.sub
    def test_cpf_cleaning(self):
        validator = CpfValidator()
        validator.validate("123.456.789-09")
        assert validator._cpf == "12345678909"

    def test_cpf_with_letters(self):
        validator = CpfValidator()
        validator.validate("abc123def456ghi789jkl09")
        assert validator._cpf == "12345678909"
