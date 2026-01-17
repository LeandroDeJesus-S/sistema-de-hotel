from unittest.mock import Mock

import pytest

from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from clients.application.services import ClientService
from clients.models import Client
from clients.feedback_messages import ChangePassword, SignUp
from exc import Result


class TestClientService:
    """Test suite for the ClientService."""

    @pytest.fixture
    def service(
        self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        mock_task_queuer,
        logger_mock,
        mock_token_manager,
    ):
        return ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )

    # --- Signup User Tests ---

    def test_signup_user_success(
        self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        mock_task_queuer,
        logger_mock,
        mock_token_manager,
        valid_client_data_factory,
    ):
        """Should successfully sign up a user and redirect to rooms."""
        # Arrange
        form_data = valid_client_data_factory()
        # Add required form fields that match DTO expectations
        form_data['nome'] = form_data.pop('first_name')
        form_data['sobrenome'] = form_data.pop('last_name')
        form_data['telefone'] = form_data.pop('phone')
        form_data['nascimento'] = form_data.pop('birthdate').strftime('%Y-%m-%d')

        request = Mock()

        mock_client_repository.check_duplicate.return_value = Result.Ok(False)
        mock_password_manager.hash_password.return_value = Result.Ok('hashed_password')
        mock_client_repository.add.return_value = Result.Ok(Mock(spec=Client))
        mock_session_manager.login.return_value = Result.Ok(None)

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.signup_user(form_data, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO), f'{dto.messages=} {form_data=}'
        assert dto.url == 'rooms'
        mock_session_manager.login.assert_called_once()

    def test_signup_user_missing_fields(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should return error when required fields are missing."""
        # Arrange
        form_data = {'username': ''}  # Missing everything else
        request = Mock()
        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )

        # Act
        result = service.signup_user(form_data, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'signup.html'
        assert any(msg.msg == str(SignUp.MISSING_FIELDS) for msg in dto.messages)

    def test_signup_user_dto_validation_error(
        self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        mock_task_queuer,
        logger_mock,
        mock_token_manager,
        mocker,
    ):
        """Should return error when SignUpInput DTO validation fails."""
        # Arrange
        form_data = {
            'username': 'validUser',
            'password': 'StrongPassword123!',
            'nome': 'John',
            'sobrenome': 'Doe',
            'telefone': '1234567890',
            'email': 'john@doe.com',
            'nascimento': '1990-01-01',
            'cpf': '12345678900',
        }
        request = Mock()
        mocker.patch(
            'clients.application.services.SignUpInput.safe_validate',
            return_value=Result.Err('DTO Validation Error'),
        )

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )

        # Act
        result = service.signup_user(form_data, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert any(msg.msg == 'DTO Validation Error' for msg in dto.messages)

    def test_signup_user_validation_error(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should return error when input validation fails (e.g. invalid email)."""
        # Arrange
        form_data = {
            'username': 'validUser',
            'password': 'StrongPassword123!',
            'nome': 'John',
            'sobrenome': 'Doe',
            'telefone': '1234567890',
            'email': 'invalid-email',  # Invalid
            'nascimento': '1990-01-01',
            'cpf': '12345678900',
        }
        request = Mock()
        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.signup_user(form_data, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert len(dto.messages) > 0

    def test_signup_user_creation_failure(
        self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        mock_task_queuer,
        logger_mock,
        mock_token_manager,
        valid_client_data_factory,
    ):
        """Should return error when user creation fails (e.g. duplicate user)."""
        # Arrange
        form_data = valid_client_data_factory()
        form_data['nome'] = form_data.pop('first_name')
        form_data['sobrenome'] = form_data.pop('last_name')
        form_data['telefone'] = form_data.pop('phone')
        form_data['nascimento'] = form_data.pop('birthdate').strftime('%Y-%m-%d')

        request = Mock()

        # Mock failure in CreateUserUseCase (e.g. duplicate check returns True)
        mock_client_repository.check_duplicate.return_value = Result.Ok(True)

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.signup_user(form_data, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        # We expect the generic SIGNUP_ERROR from usecase or "Duplicate user data"
        assert len(dto.messages) > 0

    def test_signup_user_login_failure(
        self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        mock_task_queuer,
        logger_mock,
        mock_token_manager,
        valid_client_data_factory,
    ):
        """Should return error when automatic login fails after creation."""
        # Arrange
        form_data = valid_client_data_factory()
        form_data['nome'] = form_data.pop('first_name')
        form_data['sobrenome'] = form_data.pop('last_name')
        form_data['telefone'] = form_data.pop('phone')
        form_data['nascimento'] = form_data.pop('birthdate').strftime('%Y-%m-%d')

        request = Mock()

        mock_client_repository.check_duplicate.return_value = Result.Ok(False)
        mock_password_manager.hash_password.return_value = Result.Ok('hashed')
        mock_client_repository.add.return_value = Result.Ok(Mock(spec=Client))

        mock_session_manager.login.return_value = Result.Err('Login Failed')

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )

        # Act
        result = service.signup_user(form_data, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert any([msg.msg == 'Login Failed' for msg in dto.messages]), f'{form_data=} {dto.messages=}'

    # --- Signin User Tests ---

    def test_signin_user_success(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should successfully sign in a user and redirect to next_url."""
        # Arrange
        credentials = {'username': 'user', 'password': 'password'}
        request = Mock()
        request.session = {'next_url': 'dashboard'}

        mock_session_manager.authenticate.return_value = Result.Ok(Mock(spec=Client))
        mock_session_manager.login.return_value = Result.Ok(None)

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.signin_user(credentials, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'dashboard'

    def test_signin_user_invalid_input(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should return error when credentials are invalid."""
        # Arrange
        credentials = {'username': '', 'password': ''}  # Invalid
        request = Mock()

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.signin_user(credentials, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert dto.template_name == 'signin.html'
        assert len(dto.messages) > 0

    def test_signin_user_auth_failure(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should return error when authentication fails."""
        # Arrange
        credentials = {'username': 'user', 'password': 'password'}
        request = Mock()

        mock_session_manager.authenticate.return_value = Result.Err('Invalid Credentials')

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.signin_user(credentials, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert any(msg.msg == 'Invalid Credentials' for msg in dto.messages)

    def test_signin_user_login_exception(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should return error when login process fails."""
        # Arrange
        credentials = {'username': 'user', 'password': 'password'}
        request = Mock()
        request.session = {}

        mock_session_manager.authenticate.return_value = Result.Ok(Mock(spec=Client))
        mock_session_manager.login.return_value = Result.Err('Session Error')

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.signin_user(credentials, request)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, TemplateRenderResultDTO)
        assert any(msg.msg == 'Session Error' for msg in dto.messages)

    # --- Process Password Change Tests ---

    def test_process_password_change_success(
        self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        mock_task_queuer,
        logger_mock,
        mock_token_manager,

    ):
        """Should successfully change password."""
        # Arrange
        form_data = {'new_password': 'NewPassword123!', 'password_repeat': 'NewPassword123!'}
        user_id = 1

        mock_client_repository.get_by_id.return_value = Result.Ok(Mock(spec=Client))
        mock_password_manager.hash_password.return_value = Result.Ok('hashed')
        mock_client_repository.update.return_value = Result.Ok(None)

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.process_password_change(form_data, user_id)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert dto.url == 'perfil'
        assert any(msg.msg == str(ChangePassword.SUCCESS) for msg in dto.messages)

    def test_process_password_change_validation_error(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should return error when passwords do not match."""
        # Arrange
        form_data = {'new_password': 'NewPassword123!', 'password_repeat': 'DifferentPassword'}
        user_id = 1

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.process_password_change(form_data, user_id)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert len(dto.messages) > 0
        assert any(msg.typ == 'error' for msg in dto.messages)

    def test_process_password_change_usecase_failure(self,
        mock_client_repository,
        mock_password_manager,
        mock_session_manager,
        mock_captcha_verifier,
        logger_mock,
        mock_task_queuer,
        mock_token_manager,
    ):
        """Should return error when usecase fails (e.g. user not found)."""
        # Arrange
        form_data = {'new_password': 'NewPassword123!', 'password_repeat': 'NewPassword123!'}
        user_id = 1

        mock_client_repository.get_by_id.return_value = Result.Err('User not found')

        service = ClientService(
            mock_client_repository,
            mock_password_manager,
            mock_session_manager,
            mock_captcha_verifier,
            mock_task_queuer,
            logger_mock,
            mock_token_manager,
        )
        # Act
        result = service.process_password_change(form_data, user_id)

        # Assert
        assert result.is_ok()
        dto = result.unwrap()
        assert isinstance(dto, RedirectResultDTO)
        assert any(msg.msg == 'Client not found' for msg in dto.messages)
