import pytest
from datetime import date
from unittest.mock import Mock

from django.core.management.base import CommandError

from clients.management.commands.createsuperuser import Command


class TestCreateSuperuserCommand:
    """Tests for the createsuperuser management command."""

    @pytest.fixture
    def mock_command(self, mocker):
        """Fixture providing a Command instance with mocked stdout/stderr."""
        command = Command()
        command.stdout = mocker.Mock()
        command.stderr = mocker.Mock()
        return command

    def test_handle_keyboard_interrupt(self, mocker, mock_command):
        """Should catch KeyboardInterrupt and write error message to stderr."""
        mocker.patch.object(mock_command, 'program', side_effect=KeyboardInterrupt)

        result = mock_command.handle()

        assert result is None
        mock_command.stderr.write.assert_called_once_with('command stopped')

    def test_successful_superuser_creation(self, mocker, mock_command):
        """Should create superuser with valid inputs and set proper flags."""
        # Mock all user inputs
        mock_inputs = [
            'testuser',  # username
            'John',  # name
            'Doe',  # lastname
            '1990-01-01',  # birth date
            'john@example.com',  # email
            '123456789',  # phone
            '12345678901',  # cpf
        ]
        mock_passwords = ['password123', 'password123']  # password and confirmation

        mocker.patch(
            'clients.management.commands.createsuperuser.input', side_effect=mock_inputs
        )
        mocker.patch(
            'clients.management.commands.createsuperuser.getpass', side_effect=mock_passwords
        )

        # Mock Client model
        mock_client = Mock()
        mock_client.username = 'testuser'
        mocker.patch(
            'clients.management.commands.createsuperuser.Client', return_value=mock_client
        )

        # Execute command
        mock_command.program()

        # Verify Client was created with correct data
        from clients.management.commands.createsuperuser import Client

        Client.assert_called_once_with(
            username='testuser',
            password='password123',
            first_name='John',
            last_name='Doe',
            birthdate=date(1990, 1, 1),
            email='john@example.com',
            phone='123456789',
            cpf='12345678901',
        )

        # Verify validation was called
        mock_client.full_clean.assert_called_once()

        # Verify password was set
        mock_client.set_password.assert_called_once_with('password123')

        # Verify superuser flags were set
        assert mock_client.is_superuser is True
        assert mock_client.is_staff is True

        # Verify client was saved
        mock_client.save.assert_called_once()

        # Verify success message
        mock_command.stdout.write.assert_any_call('Pass the requested informations')
        mock_command.stdout.write.assert_any_call('user successfully created: testuser')

    def test_password_mismatch(self, mocker, mock_command):
        """Should raise CommandError when passwords don't match."""
        mock_inputs = [
            'testuser',
            'John',
            'Doe',
            '1990-01-01',
            'john@example.com',
            '123456789',
            '12345678901',
        ]
        mock_passwords = ['password123', 'different_password']

        mocker.patch(
            'clients.management.commands.createsuperuser.input', side_effect=mock_inputs
        )
        mocker.patch(
            'clients.management.commands.createsuperuser.getpass', side_effect=mock_passwords
        )

        with pytest.raises(CommandError, match='passwords do not match'):
            mock_command.program()

    def test_invalid_data_validation(self, mocker, mock_command):
        """Should raise CommandError when Client validation fails."""
        mock_inputs = [
            'testuser',
            'John',
            'Doe',
            '1990-01-01',
            'john@example.com',
            '123456789',
            '12345678901',
        ]
        mock_passwords = ['password123', 'password123']

        mocker.patch(
            'clients.management.commands.createsuperuser.input', side_effect=mock_inputs
        )
        mocker.patch(
            'clients.management.commands.createsuperuser.getpass', side_effect=mock_passwords
        )

        mock_client = Mock()
        validation_error = Exception('Invalid email format')
        mock_client.full_clean.side_effect = validation_error
        mocker.patch(
            'clients.management.commands.createsuperuser.Client', return_value=mock_client
        )

        with pytest.raises(CommandError, match='invalid data: Invalid email format'):
            mock_command.program()

    def test_input_date_valid_format(self, mocker):
        """Should successfully parse valid YYYY-MM-DD date format."""
        mocker.patch(
            'clients.management.commands.createsuperuser.input', return_value='1990-01-01'
        )

        result = Command.input_date()

        assert result == date(1990, 1, 1)

    def test_input_date_invalid_format(self, mocker):
        """Should raise CommandError for invalid date format."""
        mocker.patch(
            'clients.management.commands.createsuperuser.input', return_value='01/01/1990'
        )

        with pytest.raises(
            CommandError, match='cannot convert birth date to the valid date format yyy-mm-dd'
        ):
            Command.input_date()
