import pytest
import responses
from http import HTTPStatus
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from clients.infra.adapters import DjangoPasswordManager, GoogleRecaptchaV3Verifier, DjangoSessionManager
from clients.domain.entities import Client as ClientEntity
from exc import Result

User = get_user_model()

@pytest.mark.django_db
class TestDjangoPasswordManager:
    def test_hash_password_success(self):
        manager = DjangoPasswordManager()
        result = manager.hash_password("password123")
        assert result.is_ok()
        # Should be a hashed string, not plain text
        assert result.unwrap() != "password123"
        assert "$" in result.unwrap()

    def test_hash_password_failure(self, mocker):
        manager = DjangoPasswordManager()
        mocker.patch("clients.infra.adapters.make_password", side_effect=Exception("Hash fail"))
        result = manager.hash_password("password123")
        assert result.is_err()
        assert "Failed to hash password" in result.unwrap_err().msg

    def test_check_password_success(self):
        manager = DjangoPasswordManager()
        hashed = manager.hash_password("password123").unwrap()
        result = manager.check_password("password123", hashed)
        assert result.is_ok()
        assert result.unwrap() is True

    def test_check_password_mismatch(self):
        manager = DjangoPasswordManager()
        hashed = manager.hash_password("password123").unwrap()
        result = manager.check_password("wrongpassword", hashed)
        assert result.is_err()
        assert "Password does not match" in result.unwrap_err().msg

    def test_check_password_failure(self, mocker):
        manager = DjangoPasswordManager()
        mocker.patch("clients.infra.adapters.check_password", side_effect=Exception("Check fail"))
        result = manager.check_password("password123", "hashed")
        assert result.is_err()
        assert "Failed to verify password" in result.unwrap_err().msg


class TestGoogleRecaptchaV3Verifier:
    def test_verify_success(self, responses):
        verifier = GoogleRecaptchaV3Verifier(secret_key="secret")
        responses.add(
            responses.POST,
            "https://www.google.com/recaptcha/api/siteverify",
            json={"success": True},
            status=200
        )
        result = verifier.verify("token")
        assert result.is_ok()
        assert result.unwrap() is True

    def test_verify_status_error(self, responses):
        verifier = GoogleRecaptchaV3Verifier(secret_key="secret")
        responses.add(
            responses.POST,
            "https://www.google.com/recaptcha/api/siteverify",
            status=500
        )
        result = verifier.verify("token")
        assert result.is_err()
        assert "Failed to verify captcha" in result.unwrap_err().msg

    def test_verify_invalid_captcha(self, responses):
        verifier = GoogleRecaptchaV3Verifier(secret_key="secret")
        responses.add(
            responses.POST,
            "https://www.google.com/recaptcha/api/siteverify",
            json={"success": False},
            status=200
        )
        result = verifier.verify("token")
        assert result.is_err()
        assert "Invalid captcha" in result.unwrap_err().msg


@pytest.mark.django_db
class TestDjangoSessionManager:
    @pytest.fixture
    def manager(self):
        return DjangoSessionManager()

    @pytest.fixture
    def rf(self):
        return RequestFactory()

    def _setup_request(self, rf, path):
        from django.contrib.sessions.middleware import SessionMiddleware
        request = rf.post(path)
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_authenticate_success(self, manager, rf, client_model_instance):
        request = rf.post('/login')
        result = manager.authenticate(request, client_model_instance.username, client_model_instance.raw_password)
        assert result.is_ok()
        assert result.unwrap().username == client_model_instance.username

    def test_authenticate_invalid_credentials(self, manager, rf):
        request = rf.post('/login')
        result = manager.authenticate(request, "wronguser", "wrongpass")
        assert result.is_err()
        assert "Invalid credentials" in result.unwrap_err().msg

    def test_authenticate_failure(self, manager, rf, mocker):
        request = rf.post('/login')
        mocker.patch("clients.infra.adapters.django_authenticate", side_effect=Exception("Auth error"))
        result = manager.authenticate(request, "user", "pass")
        assert result.is_err()
        assert "Failed to validate user" in result.unwrap_err().msg

    def test_authenticate_model_validate_error(self, manager, rf, client_model_instance, mocker):
        """Should return error if domain entity validation fails after authentication."""
        request = rf.post('/login')
        # Ensure authentication succeeds
        mocker.patch("clients.infra.adapters.django_authenticate", return_value=client_model_instance)
        # Mock model_validate to fail
        mocker.patch("clients.domain.entities.Client.model_validate", side_effect=Exception("Validation error"))

        result = manager.authenticate(request, client_model_instance.username, client_model_instance.raw_password)
        assert result.is_err()
        assert "Failed to validate user" in result.unwrap_err().msg

    def test_login_success(self, manager, rf, client_model_instance):
        request = self._setup_request(rf, '/login')
        # Create domain entity
        from utils.support import model_to_entity
        user_entity = model_to_entity(client_model_instance, ClientEntity).unwrap()

        result = manager.login(request, user_entity)
        assert result.is_ok()

    def test_login_invalid_user(self, manager, rf):
        request = self._setup_request(rf, '/login')
        user_entity = ClientEntity.safe_create(
            id=99999, # non-existent
            username="nonexistent",
            email="none@example.com",
            password="Password123!",
            first_name="None",
            last_name="None",
            phone="11999999999",
            cpf="12345678901",
            birthdate="1990-01-01"
        ).unwrap()

        result = manager.login(request, user_entity)
        assert result.is_err()
        assert "Invalid user" in result.unwrap_err().msg

    def test_login_failure(self, manager, rf, client_model_instance, mocker):
        request = self._setup_request(rf, '/login')
        from utils.support import model_to_entity
        user_entity = model_to_entity(client_model_instance, ClientEntity).unwrap()

        mocker.patch("clients.infra.adapters.django_login", side_effect=Exception("Login error"))
        result = manager.login(request, user_entity)
        assert result.is_err()
        assert "Failed to login user" in result.unwrap_err().msg

    def test_logout_success(self, manager, rf):
        request = self._setup_request(rf, '/logout')
        result = manager.logout(request)
        assert result.is_ok()

    def test_logout_failure(self, manager, rf, mocker):
        request = self._setup_request(rf, '/logout')
        mocker.patch("clients.infra.adapters.django_logout", side_effect=Exception("Logout error"))
        result = manager.logout(request)
        assert result.is_err()
        assert "Failed to logout user" in result.unwrap_err().msg
