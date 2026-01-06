import pytest
from datetime import date, timedelta
from clients.domain.entities import Client
from clients.feedback_messages import ClientErrorMessages

class TestClientEntity:
    def test_client_creation_success(self, valid_client_data_factory):
        data = valid_client_data_factory()
        # Ensure data types match value objects expectations
        # Birthdate VO uses date object (from PastDate)
        # Email VO uses EmailStr
        # etc.

        result = Client.safe_create(**data)
        assert result.is_ok()
        client = result.unwrap()
        assert client.username == data['username']

    def test_client_creation_missing_username(self, valid_client_data_factory):
        data = valid_client_data_factory()
        del data['username']

        result = Client.safe_create(**data)
        assert result.is_err()
        # Depending on pydantic version and how safe_validate is implemented
        # it should return the custom message
        assert result.unwrap_err().msg == ClientErrorMessages.NOT_PROVIDED_USERNAME

    def test_client_creation_invalid_email(self, valid_client_data_factory):
        data = valid_client_data_factory()
        data['email'] = "invalid-email"

        result = Client.safe_create(**data)
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.INVALID_EMAIL

    def test_client_creation_invalid_birthdate(self, valid_client_data_factory):
        data = valid_client_data_factory()
        data['birthdate'] = date.today() + timedelta(days=1) # Future

        result = Client.safe_create(**data)
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.INVALID_BIRTHDATE

    def test_client_str(self, valid_client_data_factory):
        data = valid_client_data_factory()
        client = Client.safe_create(**data).unwrap()
        assert str(client) == data['username']
