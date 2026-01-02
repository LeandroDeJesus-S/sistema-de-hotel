import logging
from unittest.mock import Mock

import pytest

from clients.application.dtos import ChangePasswordInput
from clients.application.usecases import (
    ChangePasswordUseCase,
    CreateUserUseCase,
    VerifyCaptchaUseCase,
)
from clients.domain import entities
from clients.feedback_messages import ClientErrorMessages
from exc import Error, Result


class TestCreateUserUseCase:
    """Test suite for the CreateUserUseCase."""

    def test_create_user_success(
        self, mock_client_repository, mock_password_manager
    ):
        """
        Should successfully create a user when data is valid and no duplicate exists.
        """
        # Arrange
        logger = Mock(spec=logging.Logger)
        use_case = CreateUserUseCase(mock_client_repository, mock_password_manager, logger)

        user_entity = Mock(spec=entities.Client)
        user_entity.password = "raw_password"

        mock_client_repository.check_duplicate.return_value = Result.Ok(False)
        mock_password_manager.hash_password.return_value = Result.Ok("hashed_password")
        mock_client_repository.add.return_value = Result.Ok(user_entity)

        # Act
        result = use_case(user_entity)

        # Assert
        assert result.is_ok()
        assert user_entity.password == "hashed_password"
        mock_client_repository.check_duplicate.assert_called_once_with(user_entity)
        mock_password_manager.hash_password.assert_called_once_with("raw_password")
        mock_client_repository.add.assert_called_once_with(user_entity)

    def test_create_user_duplicate_found(self, mock_client_repository, mock_password_manager):
        """
        Should return an error when a user with the same email or username already exists.
        """
        # Arrange
        logger = Mock(spec=logging.Logger)
        use_case = CreateUserUseCase(mock_client_repository, mock_password_manager, logger)

        user_entity = Mock(spec=entities.Client)
        mock_client_repository.check_duplicate.return_value = Result.Ok(True)

        # Act
        result = use_case(user_entity)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == ClientErrorMessages.SIGNUP_ERROR
        mock_client_repository.add.assert_not_called()

    def test_create_user_check_duplicate_error(self, mock_client_repository, mock_password_manager):
        """
        Should return an error if the duplicate check fails in the repository.
        """
        # Arrange
        logger = Mock(spec=logging.Logger)
        use_case = CreateUserUseCase(mock_client_repository, mock_password_manager, logger)

        user_entity = Mock(spec=entities.Client)
        error = Error("DB Error")
        mock_client_repository.check_duplicate.return_value = Result.Err("DB Error", error)

        # Act
        result = use_case(user_entity)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == "DB Error"
        mock_client_repository.add.assert_not_called()

    def test_create_user_hash_password_error(
        self, mock_client_repository, mock_password_manager
    ):
        """
        Should return an error if password hashing fails.
        """
        # Arrange
        logger = Mock(spec=logging.Logger)
        use_case = CreateUserUseCase(mock_client_repository, mock_password_manager, logger)

        user_entity = Mock(spec=entities.Client)
        user_entity.password = "raw_password"

        mock_client_repository.check_duplicate.return_value = Result.Ok(False)
        mock_password_manager.hash_password.return_value = Result.Err("Hash Error")

        # Act
        result = use_case(user_entity)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == "Failed to hash password"
        mock_client_repository.add.assert_not_called()

    def test_create_user_add_repository_error(
        self, mock_client_repository, mock_password_manager
    ):
        """
        Should return an error and log the exception if adding the user to the repository fails.
        """
        # Arrange
        logger = Mock(spec=logging.Logger)
        use_case = CreateUserUseCase(mock_client_repository, mock_password_manager, logger)

        user_entity = Mock(spec=entities.Client)
        user_entity.password = "raw_password"

        mock_client_repository.check_duplicate.return_value = Result.Ok(False)
        mock_password_manager.hash_password.return_value = Result.Ok("hashed_password")

        error = Error("Add Error")
        mock_client_repository.add.return_value = Result.Err("Add Error", error)

        # Act
        result = use_case(user_entity)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == "Add Error"
        logger.error.assert_called_once()


class TestChangePasswordUseCase:
    """Test suite for the ChangePasswordUseCase."""

    def test_change_password_success(
        self, mock_client_repository, mock_password_manager, mock_session_manager
    ):
        """
        Should successfully change the user's password when input is valid.
        """
        # Arrange
        use_case = ChangePasswordUseCase(
            mock_client_repository, mock_password_manager, mock_session_manager
        )
        input_dto = ChangePasswordInput(
            user_id=1, password="new_password", password_repeat="new_password"
        )

        mock_client_repository.get_by_id.return_value = Result.Ok(Mock(spec=entities.Client))
        mock_password_manager.hash_password.return_value = Result.Ok("hashed_new_password")
        mock_client_repository.update.return_value = Result.Ok(None)

        # Act
        result = use_case(input_dto)

        # Assert
        assert result.is_ok()
        mock_client_repository.get_by_id.assert_called_once_with(1)
        mock_password_manager.hash_password.assert_called_once_with("new_password")
        mock_client_repository.update.assert_called_once_with(1, password="hashed_new_password")

    def test_change_password_user_not_found(
        self, mock_client_repository, mock_password_manager, mock_session_manager
    ):
        """
        Should return an error if the user is not found.
        """
        # Arrange
        use_case = ChangePasswordUseCase(
            mock_client_repository, mock_password_manager, mock_session_manager
        )
        input_dto = ChangePasswordInput(
            user_id=1, password="new_password", password_repeat="new_password"
        )
        mock_client_repository.get_by_id.return_value = Result.Err("Not Found")

        # Act
        result = use_case(input_dto)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == "Client not found"
        mock_client_repository.update.assert_not_called()

    def test_change_password_hash_error(
        self, mock_client_repository, mock_password_manager, mock_session_manager
    ):
        """
        Should return an error if password hashing fails.
        """
        # Arrange
        use_case = ChangePasswordUseCase(
            mock_client_repository, mock_password_manager, mock_session_manager
        )
        input_dto = ChangePasswordInput(
            user_id=1, password="new_password", password_repeat="new_password"
        )
        mock_client_repository.get_by_id.return_value = Result.Ok(Mock())
        mock_password_manager.hash_password.return_value = Result.Err("Hash Error")

        # Act
        result = use_case(input_dto)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == "Failed to hash password"
        mock_client_repository.update.assert_not_called()

    def test_change_password_update_error(
        self, mock_client_repository, mock_password_manager, mock_session_manager
    ):
        """
        Should return an error if updating the password in the repository fails.
        """
        # Arrange
        use_case = ChangePasswordUseCase(
            mock_client_repository, mock_password_manager, mock_session_manager
        )
        input_dto = ChangePasswordInput(
            user_id=1, password="new_password", password_repeat="new_password"
        )
        mock_client_repository.get_by_id.return_value = Result.Ok(Mock())
        mock_password_manager.hash_password.return_value = Result.Ok("hashed")
        mock_client_repository.update.return_value = Result.Err("Update Error")

        # Act
        result = use_case(input_dto)

        # Assert
        assert result.is_err()
        assert result.unwrap_err().msg == "Failed to update password"


class TestVerifyCaptchaUseCase:
    """Test suite for the VerifyCaptchaUseCase."""

    def test_verify_captcha_success(self, mock_captcha_verifier):
        """
        Should return True when the captcha service validates the token.
        """
        # Arrange
        use_case = VerifyCaptchaUseCase(mock_captcha_verifier)
        mock_captcha_verifier.verify.return_value = Result.Ok(True)

        # Act
        result = use_case("token")

        # Assert
        assert result.is_ok()
        assert result.unwrap() is True
        mock_captcha_verifier.verify.assert_called_once_with("token")

    def test_verify_captcha_failure(self, mock_captcha_verifier):
        """
        Should return False when the captcha service rejects the token.
        """
        # Arrange
        use_case = VerifyCaptchaUseCase(mock_captcha_verifier)
        mock_captcha_verifier.verify.return_value = Result.Ok(False)

        # Act
        result = use_case("token")

        # Assert
        assert result.is_ok()
        assert result.unwrap() is False

    def test_verify_captcha_error(self, mock_captcha_verifier):
        """
        Should return an error when the captcha service encounters an error.
        """
        # Arrange
        use_case = VerifyCaptchaUseCase(mock_captcha_verifier)
        mock_captcha_verifier.verify.return_value = Result.Err("Error")

        # Act
        result = use_case("token")

        # Assert
        assert result.is_err()
