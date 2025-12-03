"""
Tests for the Client model.
"""

from datetime import datetime, timedelta

import pytest
from ddf import G
from django.core.exceptions import ValidationError

from clients.models import Client
from clients.feedback_messages import ClientErrorMessages, ContactErrorMessages
from clients.rules import ClientRules


@pytest.mark.django_db
def test_client_model_creation_with_valid_data():
    """
    Tests if a client is saved to the database if all
    the data sent is valid.
    """
    # Arrange
    client = G(Client)

    # Act & Assert
    assert Client.objects.filter(pk=client.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'username, error_message',
    [
        (
            'a' * (ClientRules.USERNAME_MIN_SIZE - 1),
            ClientErrorMessages.INVALID_USERNAME_LEN % {
                    'min_len': ClientRules.USERNAME_MIN_SIZE,
                    'max_len': ClientRules.USERNAME_MAX_SIZE,
            },
        ),
        (
            'a' * (ClientRules.USERNAME_MAX_SIZE + 1),
            ClientErrorMessages.INVALID_USERNAME_LEN % {
                    'min_len': ClientRules.USERNAME_MIN_SIZE,
                    'max_len': ClientRules.USERNAME_MAX_SIZE,
            },
        ),
        (
            'Avd/d123#',
            ClientErrorMessages.INVALID_USERNAME_CHARS,
        ),
    ],
)
def test_invalid_username_raises_validation_error(username, error_message, valid_client_data_factory):
    """
    Tests if invalid username raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['username'] = username
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert error_message in excinfo.value.messages


@pytest.mark.django_db
def test_duplicated_username_raises_validation_error(valid_client_data_factory):
    """
    Tests if a duplicated username raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    G(Client, username=valid_client_data['username'])
    other_client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        other_client.full_clean()
    assert ClientErrorMessages.DUPLICATED_USERNAME in excinfo.value.messages


@pytest.mark.django_db
def test_blank_username_raises_validation_error(valid_client_data_factory):
    """
    Tests if a blank username raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['username'] = ''
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert ClientErrorMessages.NOT_PROVIDED_USERNAME in excinfo.value.messages


@pytest.mark.django_db
@pytest.mark.parametrize(
    'password', ['1234567', 'abcdefegguda', '45648998464', 'fdsjfsdfj7879878']
)
def test_weak_password_raises_validation_error(password, valid_client_data_factory):
    """
    Tests if a weak password raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['password'] = password
    client = Client(**valid_client_data)
    expected_msg = ClientErrorMessages.PASSWORD_WEAK % {
        'min_len': ClientRules.PASSWORD_MIN_SIZE,
        'max_len': ClientRules.PASSWORD_MAX_SIZE,
        'symbols': ClientRules.PASSWORD_SUPPORTED_SYMBOLS,
    }

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert expected_msg in excinfo.value.messages


@pytest.mark.django_db
@pytest.mark.parametrize(
    'first_name, error_message',
    [
        (
            'a' * (ClientRules.MIN_FIRSTNAME_CHARS - 1),
            ClientErrorMessages.INVALID_FIRSTNAME_MIN_LENGTH,
        ),
        (
            'a' * (ClientRules.MAX_FIRSTNAME_CHARS + 1),
            ClientErrorMessages.INVALID_FIRSTNAME_MAX_LENGTH,
        ),
        ('teste123', ClientErrorMessages.INVALID_FIRSTNAME_LETTERS),
        ('12343', ClientErrorMessages.INVALID_FIRSTNAME_LETTERS),
        ('teste@', ClientErrorMessages.INVALID_FIRSTNAME_LETTERS),
        ('teste ', ClientErrorMessages.INVALID_FIRSTNAME_LETTERS),
    ],
)
def test_invalid_first_name_raises_validation_error(
    first_name, error_message, valid_client_data_factory
):
    """
    Tests if an invalid first_name raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['first_name'] = first_name
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert error_message in excinfo.value.messages


@pytest.mark.django_db
@pytest.mark.parametrize(
    'last_name, error_message',
    [
        (
            'a' * (ClientRules.MIN_SURNAME_CHARS - 1),
            ClientErrorMessages.INVALID_SURNAME_MIN_LENGTH,
        ),
        (
            'a' * (ClientRules.MAX_SURNAME_CHARS + 1),
            ClientErrorMessages.INVALID_SURNAME_MAX_LENGTH,
        ),
        ('teste123', ClientErrorMessages.INVALID_SURNAME_LETTERS),
        ('12343', ClientErrorMessages.INVALID_SURNAME_LETTERS),
        ('teste@', ClientErrorMessages.INVALID_SURNAME_LETTERS),
        ('teste_teste', ClientErrorMessages.INVALID_SURNAME_LETTERS),
    ],
)
def test_invalid_last_name_raises_validation_error(
    last_name, error_message, valid_client_data_factory
):
    """
    Tests if an invalid last_name raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['last_name'] = last_name
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert error_message in excinfo.value.messages


def test_complete_name_property(valid_client_data_factory):
    """
    Tests if the complete_name property returns the full name.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    client = Client(**valid_client_data)
    expected_complete_name = (
        f'{valid_client_data["first_name"]} {valid_client_data["last_name"]}'
    )

    # Act
    result = client.complete_name

    # Assert
    assert result == expected_complete_name



@pytest.mark.django_db
@pytest.mark.parametrize(
    'birthdate, error_message',
    [
        (
            datetime.now().date().replace(
                year=datetime.now().year - (ClientRules.MIN_AGE - 1)
            ),
            ClientErrorMessages.INVALID_BIRTHDATE,
        ),
        (
            datetime.now().date().replace(
                year=datetime.now().year - (ClientRules.MAX_AGE + 1)
            ),
            ClientErrorMessages.INVALID_BIRTHDATE,
        ),
    ],
)
def test_invalid_birthdate_raises_validation_error(
    birthdate, error_message, valid_client_data_factory
):
    """
    Tests if an invalid birthdate raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['birthdate'] = birthdate
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert error_message in excinfo.value.messages


def test_age_property(valid_client_data_factory):
    """
    Tests if the age property returns the correct age.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    client = Client(**valid_client_data)
    expected_age = datetime.now().year - valid_client_data['birthdate'].year

    # Act
    result = client.age

    # Assert
    assert result == expected_age


def test_masked_email_property(valid_client_data_factory):
    """
    Tests if the masked_email property returns the email with masked characters.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    client = Client(**valid_client_data)
    email = valid_client_data['email']
    start, end = ClientRules.EMAIL_MASK_RANGE
    end = len(email) + end
    expected_masked_email = ''.join([
        '*' if start <= i <= end else char for i, char in enumerate(email)
    ])

    # Act
    result = client.masked_email

    # Assert
    assert result == expected_masked_email


@pytest.mark.django_db
@pytest.mark.parametrize('email', ['email.com', 'email', 'email@invalid'])
def test_invalid_email_raises_validation_error(email, valid_client_data_factory):
    """
    Tests if an invalid email raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['email'] = email
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert ContactErrorMessages.INVALID_EMAIL in excinfo.value.messages


def test_formatted_phone_property(valid_client_data_factory):
    """
    Tests if the formatted_phone property returns the phone formatted.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    client = Client(**valid_client_data)
    phone = valid_client_data['phone']
    expected_formatted_phone = f'({phone[:2]}) {phone[2:-4]}-{phone[-4:]}'

    # Act
    result = client.formatted_phone

    # Assert
    assert result == expected_formatted_phone


def test_masked_phone_property(valid_client_data_factory):
    """
    Tests if the masked_phone property returns the phone with masked characters.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    client = Client(**valid_client_data)
    phone = valid_client_data['phone']
    start, end = ClientRules.PHONE_MASK_RANGE
    end = len(phone) + end
    expected_masked_phone = ''.join([
        '*' if start <= i <= end else char for i, char in enumerate(phone)
    ])

    # Act
    result = client.masked_phone

    # Assert
    assert result == expected_masked_phone


@pytest.mark.django_db
def test_cpf_sequence_raises_validation_error(valid_client_data_factory):
    """
    Tests if a CPF sequence raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['cpf'] = '1' * 11
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert ClientErrorMessages.INVALID_CPF in excinfo.value.messages


@pytest.mark.django_db
def test_invalid_cpf_raises_validation_error(valid_client_data_factory):
    """
    Tests if an invalid CPF raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    valid_client_data['cpf'] = '11111111111'
    client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        client.full_clean()
    assert ClientErrorMessages.INVALID_CPF in excinfo.value.messages


def test_masked_cpf_property(valid_client_data_factory):
    """
    Tests if the masked_cpf property returns the cpf with masked characters.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    client = Client(**valid_client_data)
    cpf = valid_client_data['cpf']
    start, end = ClientRules.CPF_MASK_RANGE
    end = len(cpf) + end
    expected_masked_cpf = ''.join([
        '*' if start <= i <= end else char for i, char in enumerate(cpf)
    ])

    # Act
    result = client.masked_cpf

    # Assert
    assert result == expected_masked_cpf


@pytest.mark.django_db
def test_duplicated_cpf_raises_validation_error(valid_client_data_factory):
    """
    Tests if a duplicated CPF raises a ValidationError.
    """
    # Arrange
    valid_client_data = valid_client_data_factory()
    G(Client, cpf=valid_client_data['cpf'])
    other_client = Client(**valid_client_data)

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        other_client.full_clean()
    assert ClientErrorMessages.DUPLICATED_CPF in excinfo.value.messages
