import logging
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User

from clients.domain.entities import Client
from clients.infra.adapters import (
    DjangoPasswordManager,
    DjangoSessionManager,
    GoogleRecaptchaV3Verifier,
)
from exc import Error

logger = logging.getLogger('djangoLogger')


@pytest.fixture
def password_manager():
    return DjangoPasswordManager()


@pytest.fixture
def recaptcha_verifier():
    return GoogleRecaptchaV3Verifier(secret_key='fake-secret-key')


@pytest.fixture
def session_manager():
    return DjangoSessionManager()


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.pk = 1
    user.id = 1
    user.username = 'testuser'
    user.password = 'hashed_password'
    user.first_name = 'Test'
    user.last_name = 'User'
    user.email = 'test@example.com'
    user.birthdate = '2000-01-01'
    user.phone = '11999999999'
    user.cpf = '11122233344'

    # Simulate the __dict__ for model_validate
    user.__dict__.update({
        'pk': user.pk,
        'id': user.id,
        'username': user.username,
        'password': user.password,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'birthdate': user.birthdate,
        'phone': user.phone,
        'cpf': user.cpf,
    })
    return user


# --- Tests for DjangoPasswordManager ---

def test_hash_password_success(password_manager):
    raw_password = 'plain_password'
    result = password_manager.hash_password(raw_password)
    assert result.error is None
    assert result.value is not None
    assert result.value != raw_password


def test_check_password_success(password_manager):
    raw_password = 'plain_password'
    hashed_result = password_manager.hash_password(raw_password)
    check_result = password_manager.check_password(raw_password, hashed_result.value)
    assert check_result.error is None
    assert check_result.value is True


def test_check_password_failure(password_manager):
    raw_password = 'plain_password'
    wrong_password = 'wrong_password'
    hashed_result = password_manager.hash_password(raw_password)
    check_result = password_manager.check_password(wrong_password, hashed_result.value)
    assert check_result.error is not None
    assert not check_result.value


def test_hash_password_exception(password_manager, mocker):
    mocker.patch(
        'clients.infra.adapters.make_password', side_effect=Exception('Hashing error')
    )
    result = password_manager.hash_password('any_password')
    assert result.value is None
    assert isinstance(result.error, Error)
    assert 'Failed to hash password' in result.error.msg


def test_check_password_exception(password_manager, mocker):
    mocker.patch(
        'clients.infra.adapters.check_password',
        side_effect=Exception('Verification error'),
    )
    result = password_manager.check_password('any_password', 'any_hash')
    assert not result.value
    assert isinstance(result.error, Error)
    assert 'Failed to verify password' in result.error.msg


# --- Tests for GoogleRecaptchaV3Verifier ---

def test_recaptcha_verify_success(recaptcha_verifier, mocker):
    mock_post = mocker.patch('clients.infra.adapters.requests.post')
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {'success': True}
    mock_post.return_value = mock_response

    result = recaptcha_verifier.verify('fake-token')

    assert result.error is None
    assert result.value is True


def test_recaptcha_verify_http_error(recaptcha_verifier, mocker):
    mock_post = mocker.patch('clients.infra.adapters.requests.post')
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    mock_post.return_value = mock_response

    result = recaptcha_verifier.verify('fake-token')

    assert not result.value
    assert isinstance(result.error, Error)
    assert 'Failed to verify captcha' in result.error.msg


def test_recaptcha_verify_captcha_failure(recaptcha_verifier, mocker):
    mock_post = mocker.patch('clients.infra.adapters.requests.post')
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {'success': False}
    mock_post.return_value = mock_response

    result = recaptcha_verifier.verify('fake-token')

    assert not result.value
    assert isinstance(result.error, Error)
    assert 'Invalid captcha' in result.error.msg


# --- Tests for DjangoSessionManager ---

def test_authenticate_success(session_manager, mock_user, mocker):
    mock_django_authenticate = mocker.patch('clients.infra.adapters.django_authenticate')
    mock_django_authenticate.return_value = mock_user

    result = session_manager.authenticate(
        request=MagicMock(), username='testuser', password='password'
    )

    assert result.error is None
    assert isinstance(result.value, Client)
    assert result.value.username == 'testuser'


def test_authenticate_failure(session_manager, mocker):
    mocker.patch('clients.infra.adapters.django_authenticate', return_value=None)
    result = session_manager.authenticate(
        request=MagicMock(), username='testuser', password='wrong_password'
    )

    assert result.value is None
    assert isinstance(result.error, Error)
    assert 'Invalid credentials' in result.error.msg


def test_authenticate_exception(session_manager, mocker):
    mocker.patch(
        'clients.infra.adapters.django_authenticate',
        side_effect=Exception('Auth backend error'),
    )
    result = session_manager.authenticate(
        request=MagicMock(), username='testuser', password='password'
    )

    assert result.value is None
    assert isinstance(result.error, Error)
    assert 'Failed to validate user' in result.error.msg


def test_login_success(session_manager, mock_user, mocker):
    mock_django_login = mocker.patch('clients.infra.adapters.django_login')

    # Patch the model on the instance to prevent DB access
    mock_usermodel = MagicMock()
    session_manager._usermodel = mock_usermodel
    mock_queryset = MagicMock()
    mock_usermodel.objects.filter.return_value = mock_queryset
    mock_queryset.first.return_value = mock_user

    client_entity = Client.model_validate(mock_user.__dict__)

    result = session_manager.login(request=MagicMock(), user=client_entity)

    assert result.error is None
    mock_django_login.assert_called_once()


def test_login_user_not_found(session_manager, mock_user, mocker):
    # Patch the model on the instance to prevent DB access
    mock_usermodel = MagicMock()
    session_manager._usermodel = mock_usermodel
    mock_queryset = MagicMock()
    mock_usermodel.objects.filter.return_value = mock_queryset
    mock_queryset.first.return_value = None

    client_entity = Client.model_validate(mock_user.__dict__)

    result = session_manager.login(request=MagicMock(), user=client_entity)

    assert result.value is None
    assert isinstance(result.error, Error)
    assert 'Invalid user' in result.error.msg


def test_login_exception(session_manager, mock_user, mocker):
    mocker.patch(
        'clients.infra.adapters.django_login', side_effect=Exception('Login error')
    )

    # Patch the model on the instance to prevent DB access
    mock_usermodel = MagicMock()
    session_manager._usermodel = mock_usermodel
    mock_queryset = MagicMock()
    mock_usermodel.objects.filter.return_value = mock_queryset
    mock_queryset.first.return_value = mock_user

    client_entity = Client.model_validate(mock_user.__dict__)

    result = session_manager.login(request=MagicMock(), user=client_entity)

    assert result.value is None
    assert isinstance(result.error, Error)
    assert 'Failed to login user' in result.error.msg


def test_logout_success(session_manager, mocker):
    mock_django_logout = mocker.patch('clients.infra.adapters.django_logout')
    result = session_manager.logout(request=MagicMock())
    assert result.error is None
    mock_django_logout.assert_called_once()


def test_logout_exception(session_manager, mocker):
    mocker.patch(
        'clients.infra.adapters.django_logout', side_effect=Exception('Logout error')
    )
    result = session_manager.logout(request=MagicMock())
    assert result.value is None
    assert isinstance(result.error, Error)
    assert 'Failed to logout user' in result.error.msg
