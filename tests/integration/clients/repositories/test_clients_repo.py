import pytest
from unittest.mock import Mock
from clients.infra.repo import ClientRepository
from clients.domain.entities import Client
from clients.models import Client as DjangoClient
from exc import Result

@pytest.mark.django_db
class TestClientRepository:
    @pytest.fixture
    def repo(self, logger_mock):
        return ClientRepository(logger=logger_mock)

    def test_add_success(self, repo, valid_client_data_factory):
        """Should successfully add a client."""
        data = valid_client_data_factory()
        client_entity = Client.safe_create(**data).unwrap()

        result = repo.add(client_entity)

        assert result.is_ok()
        saved_client = result.unwrap()
        assert saved_client.id is not None
        assert saved_client.username == data['username']
        assert DjangoClient.objects.filter(id=saved_client.id).exists()

    def test_add_conversion_error(self, repo, valid_client_data_factory, mocker):
        """Should return Err if entity_to_model fails."""
        data = valid_client_data_factory()
        client_entity = Client.safe_create(**data).unwrap()

        mocker.patch('clients.infra.repo.entity_to_model', return_value=Result.Err("Conversion error"))

        result = repo.add(client_entity)
        assert result.is_err()
        assert result.unwrap_err().msg == "Conversion error"

    def test_add_validation_error(self, repo, valid_client_data_factory, mocker):
        """Should return Err if model_validate fails."""
        data = valid_client_data_factory()
        client_entity = Client.safe_create(**data).unwrap()

        mocker.patch('clients.infra.repo.entity_to_model', return_value=Result.Ok(Mock()))
        mocker.patch('clients.infra.repo.model_validate', return_value=Result.Err("Validation error"))

        result = repo.add(client_entity)
        assert result.is_err()
        assert result.unwrap_err().msg == "Validation error"

    def test_add_save_exception(self, repo, valid_client_data_factory, mocker):
        """Should fail if save raises exception."""
        data = valid_client_data_factory()
        client_entity = Client.safe_create(**data).unwrap()

        # Mock model instance save to raise
        mock_model = Mock()
        mock_model.save.side_effect = Exception("DB Error")

        mocker.patch('clients.infra.repo.entity_to_model', return_value=Result.Ok(mock_model))
        mocker.patch('clients.infra.repo.model_validate', return_value=Result.Ok(mock_model))

        result = repo.add(client_entity)

        assert result.is_err()
        assert result.unwrap_err().msg == "Could not save client"

    def test_get_by_id_success(self, repo, client_model_instance):
        """Should return client by id."""
        result = repo.get_by_id(client_model_instance.id)
        assert result.is_ok()
        assert result.unwrap().id == client_model_instance.id

    def test_get_by_id_not_found(self, repo):
        """Should return Err if not found."""
        result = repo.get_by_id(99999)
        assert result.is_err()
        assert "does not exist" in result.unwrap_err().msg

    def test_get_by_id_exception(self, repo, mocker):
        """Should return Err on generic exception."""
        mocker.patch('clients.models.Client.objects.get', side_effect=Exception("Boom"))
        result = repo.get_by_id(1)
        assert result.is_err()
        assert "Could not retrieve client" in result.unwrap_err().msg

    def test_get_by_username_success(self, repo, client_model_instance):
        result = repo.get_by_username(client_model_instance.username)
        assert result.is_ok()
        assert result.unwrap().username == client_model_instance.username

    def test_get_by_username_not_found(self, repo):
        result = repo.get_by_username("nonexistent")
        assert result.is_err()
        assert "does not exist" in result.unwrap_err().msg

    def test_get_by_username_exception(self, repo, mocker):
        mocker.patch('clients.models.Client.objects.get', side_effect=Exception("Boom"))
        result = repo.get_by_username("user")
        assert result.is_err()
        assert "Could not retrieve client" in result.unwrap_err().msg

    def test_get_by_email_success(self, repo, client_model_instance):
        result = repo.get_by_email(client_model_instance.email)
        assert result.is_ok()
        assert result.unwrap().email == client_model_instance.email

    def test_get_by_email_not_found(self, repo):
        result = repo.get_by_email("nonexistent@example.com")
        assert result.is_err()
        assert "does not exist" in result.unwrap_err().msg

    def test_get_by_email_exception(self, repo, mocker):
        mocker.patch('clients.models.Client.objects.get', side_effect=Exception("Boom"))
        result = repo.get_by_email("email@example.com")
        assert result.is_err()
        assert "Could not retrieve client" in result.unwrap_err().msg

    def test_update_success(self, repo, client_model_instance):
        result = repo.update(client_model_instance.id, first_name="Updated")
        assert result.is_ok()
        client_model_instance.refresh_from_db()
        assert client_model_instance.first_name == "Updated"

    def test_update_not_found(self, repo):
        result = repo.update(99999, first_name="Updated")
        assert result.is_err()
        assert "does not exist" in result.unwrap_err().msg

    def test_update_exception(self, repo, mocker):
        mocker.patch('clients.models.Client.objects.get', side_effect=Exception("Boom"))
        result = repo.update(1, first_name="Updated")
        assert result.is_err()
        assert "Could not update client" in result.unwrap_err().msg

    def test_delete_success(self, repo, client_model_instance):
        result = repo.delete(client_model_instance.id)
        assert result.is_ok()
        assert not DjangoClient.objects.filter(id=client_model_instance.id).exists()

    def test_delete_not_found(self, repo):
        result = repo.delete(99999)
        assert result.is_err()
        assert "does not exist" in result.unwrap_err().msg

    def test_delete_exception(self, repo, client_model_instance, mocker):
        # We need to mock delete to raise, but retrieve to succeed
        client_mock = Mock()
        client_mock.delete.side_effect = Exception("Boom")
        mocker.patch('clients.models.Client.objects.get', return_value=client_mock)

        result = repo.delete(client_model_instance.id)
        assert result.is_err()
        assert "Could not delete client" in result.unwrap_err().msg

    def test_check_duplicate_true(self, repo, client_model_instance):
        # Create entity with conflicting data
        entity = Client.safe_create(
            username=client_model_instance.username, # conflict
            password="Password123!",
            first_name="Test",
            last_name="Test",
            email="other@example.com",
            phone="1234567890",
            cpf="12345678901",
            birthdate="1990-01-01"
        ).unwrap()

        result = repo.check_duplicate(entity)
        assert result.is_ok()
        assert result.unwrap() is True

    def test_check_duplicate_false(self, repo, valid_client_data_factory):
        data = valid_client_data_factory()
        entity = Client.safe_create(**data).unwrap()

        result = repo.check_duplicate(entity)
        assert result.is_ok()
        assert result.unwrap() is False

    def test_check_duplicate_exclude_self(self, repo, client_model_instance):
        # Convert model to entity to have same ID
        from utils.support import model_to_entity
        entity = model_to_entity(client_model_instance, Client).unwrap()

        # Should return False because it matches itself
        result = repo.check_duplicate(entity)
        assert result.is_ok()
        assert result.unwrap() is False

    def test_check_duplicate_exception(self, repo, valid_client_data_factory, mocker):
        data = valid_client_data_factory()
        entity = Client.safe_create(**data).unwrap()

        mocker.patch('clients.models.Client.objects.filter', side_effect=Exception("Boom"))

        result = repo.check_duplicate(entity)
        assert result.is_err()
        assert "Could not check for duplicate client" in result.unwrap_err().msg
