
import pytest
from unittest.mock import MagicMock, patch
from clients.infra.repo import ClientRepository
from clients.domain.entities import Client as ClientEntity
from clients.models import Client as DjangoClient
from exc import Result, Error
from django.db.models import Q

@pytest.fixture
def client_repository():
    return ClientRepository()

@pytest.fixture
def client_entity_fixture():
    return ClientEntity.safe_create(
        first_name="John",
        last_name="Doe",
        username="johndoe",
        email="johndoe@example.com",
        phone="(11) 99999-9999",
        password="password123",
        birthdate="1990-01-01",
        cpf="123.456.789-01"
    )

@pytest.mark.django_db
def test_add_success(client_repository, client_entity_fixture, mocker):
    mocker.patch.object(DjangoClient, 'save')
    mocker.patch.object(DjangoClient, 'full_clean')
    mocker.patch('clients.infra.repo.ClientRepository._to_entity', return_value=client_entity_fixture)

    result = client_repository.add(client_entity_fixture.unwrap())

    assert isinstance(result, Result)
    assert result.unwrap() == client_entity_fixture.unwrap()
    assert result.is_ok()

@pytest.mark.django_db
def test_add_failure(client_repository, client_entity_fixture, mocker):
    mocker.patch.object(DjangoClient, 'save', side_effect=Exception("DB error"))
    mocker.patch.object(DjangoClient, 'full_clean')  # Mock validation to isolate save error

    result = client_repository.add(client_entity_fixture.unwrap())

    assert isinstance(result, Result)
    assert result.is_err()
    assert isinstance(result.unwrap_err(), Error)

@pytest.mark.django_db
def test_get_by_id_success(client_repository, client_entity_fixture, mocker):
    mock_django_client = MagicMock(spec=DjangoClient)
    mocker.patch.object(DjangoClient.objects, 'get', return_value=mock_django_client)
    mocker.patch('clients.infra.repo.ClientRepository._to_entity', return_value=client_entity_fixture)

    result = client_repository.get_by_id(1)

    assert isinstance(result, Result)
    assert result.unwrap() == client_entity_fixture.unwrap()
    assert result.is_ok()

@pytest.mark.django_db
def test_get_by_id_not_found(client_repository, mocker):
    mocker.patch.object(DjangoClient.objects, 'get', side_effect=DjangoClient.DoesNotExist)

    result = client_repository.get_by_id(1)

    assert isinstance(result, Result)
    assert result.is_err()
    assert isinstance(result.unwrap_err(), Error)
    assert result.unwrap_err().msg == 'Client with id 1 does not exist.'

@pytest.mark.django_db
def test_update_success(client_repository, mocker):
    mock_django_client = MagicMock(spec=DjangoClient)
    mocker.patch.object(DjangoClient.objects, 'get', return_value=mock_django_client)
    mocker.patch('clients.infra.repo.update_changed_fields', return_value=None)

    result = client_repository.update(1, first_name="Jane")

    assert isinstance(result, Result)
    assert result.is_ok()

@pytest.mark.django_db
def test_delete_success(client_repository, mocker):
    mock_django_client = MagicMock(spec=DjangoClient)
    mocker.patch.object(DjangoClient.objects, 'get', return_value=mock_django_client)

    result = client_repository.delete(1)

    assert isinstance(result, Result)
    assert result.is_ok()
    mock_django_client.delete.assert_called_once()

@pytest.mark.django_db
def test_check_duplicate_exists(client_repository, client_entity_fixture, mocker):
    mocker.patch.object(DjangoClient.objects, 'filter', return_value=MagicMock(exists=lambda: True))

    result = client_repository.check_duplicate(client_entity_fixture.unwrap())

    assert isinstance(result, Result)
    assert result.unwrap() is True
    assert result.is_ok()

@pytest.mark.django_db
def test_check_duplicate_not_exists(client_repository, client_entity_fixture, mocker):
    mocker.patch.object(DjangoClient.objects, 'filter', return_value=MagicMock(exists=lambda: False))

    result = client_repository.check_duplicate(client_entity_fixture.unwrap())

    assert isinstance(result, Result)
    assert result.unwrap() is False
    assert result.is_ok()
