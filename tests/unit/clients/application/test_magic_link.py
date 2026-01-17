from unittest.mock import Mock, patch
import pytest
from clients.application.services import ClientService
from clients.domain.entities import Client
from exc import Result
from base.dtos import TemplateRenderResultDTO

class TestMagicLink:
    @pytest.fixture
    def service(self, mock_client_repository, mock_password_manager, mock_session_manager,
                mock_captcha_verifier, mock_task_queuer, logger_mock, mock_token_manager):
        return ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager
        )

    def test_request_magic_link_success(self, service, mock_client_repository, mock_task_queuer, mock_token_manager):
        # Arrange
        email = "test@example.com"
        domain = "localhost:8000"
        client = Mock(spec=Client)
        client.id = 1
        client.email = email

        mock_client_repository.get_by_email.return_value = Result.Ok(client)
        mock_token_manager.make_token.return_value = "fake-token"

        # Act
        result = service.request_magic_link(email, domain)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'request_magic_link.html'
        mock_task_queuer.queue_task.assert_called_once()
        args, kwargs = mock_task_queuer.queue_task.call_args
        assert args[1] == (1, "fake-token", domain)

    def test_request_magic_link_user_not_found(self, service, mock_client_repository, mock_task_queuer):
        # Arrange
        email = "nonexistent@example.com"
        domain = "localhost:8000"
        mock_client_repository.get_by_email.return_value = Result.Err("Not found")

        # Act
        result = service.request_magic_link(email, domain)

        # Assert
        assert result.is_ok() # We return Ok with generic message for security
        dto = result.unwrap()
        assert dto.template_name == 'request_magic_link.html'
        mock_task_queuer.queue_task.assert_not_called()

    def test_validate_magic_link_token_success(self, service, mock_client_repository, mock_token_manager):
        # Arrange
        user_id = 1
        token = "valid-token"
        client = Mock(spec=Client)
        mock_client_repository.get_by_id.return_value = Result.Ok(client)
        mock_token_manager.check_token.return_value = True

        # Act
        is_valid = service.validate_magic_link_token(user_id, token)

        # Assert
        assert is_valid is True
        mock_token_manager.check_token.assert_called_once_with(client, token)

    def test_validate_magic_link_token_invalid(self, service, mock_client_repository, mock_token_manager):
        # Arrange
        user_id = 1
        token = "invalid-token"
        client = Mock(spec=Client)
        mock_client_repository.get_by_id.return_value = Result.Ok(client)
        mock_token_manager.check_token.return_value = False

        # Act
        is_valid = service.validate_magic_link_token(user_id, token)

        # Assert
        assert is_valid is False
