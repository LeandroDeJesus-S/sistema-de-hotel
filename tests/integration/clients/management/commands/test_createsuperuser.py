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

    @pytest.mark.django_db
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
            '11144477735',  # cpf
        ]
        mock_passwords = ['Password123!', 'Password123!']  # password and confirmation

        mocker.patch(
            'clients.management.commands.createsuperuser.input', side_effect=mock_inputs
        )
        mocker.patch(
            'clients.management.commands.createsuperuser.getpass', side_effect=mock_passwords
        )

        # Execute command
        mock_command.program()

        # Verify Client was created in database
        from clients.models import Client

        client = Client.objects.get(username='testuser')

        assert client.first_name == 'John'
        assert client.last_name == 'Doe'
        assert client.birthdate == date(1990, 1, 1)
        assert client.email == 'john@example.com'
        assert client.phone == '123456789'
        assert client.cpf == '11144477735'
        assert client.is_superuser is True
        assert client.is_staff is True

        # Verify success message
        mock_command.stdout.write.assert_any_call('Pass the requested informations')
        mock_command.stdout.write.assert_any_call('user successfully created: testuser')

        # Cleanup
        client.delete()

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

    @pytest.mark.django_db
    def test_invalid_data_validation(self, mocker, mock_command):
        """Should raise CommandError when Client validation fails."""
        mock_inputs = [
            'testuser',
            'John',
            'Doe',
            '1990-01-01',
            'invalid-email',  # invalid email
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

        with pytest.raises(CommandError, match='invalid data'):
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
