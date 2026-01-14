from datetime import datetime
from getpass import getpass
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from clients.models import Client


class Command(BaseCommand):
    """
    Django management command to create a superuser with extended client information.
    """

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            self.program(*args, **options)
        except KeyboardInterrupt:
            self.stderr.write('command stopped')
        return None

    def program(self, *args, **options):
        self.stdout.write('Please provide the requested information.')

        username = input('username: ').strip()
        password = getpass().strip()
        pass_confirm = getpass('Confirm password: ').strip()

        name = input('name: ').strip()
        lastname = input('lastname: ').strip()
        bdate = self.input_date()
        email = input('email: ').strip()
        phone = input('phone: ').strip()
        cpf = input('cpf: ').strip()

        if password != pass_confirm:
            raise CommandError('Passwords do not match.')

        c = Client(
            username=username,
            password=password,
            first_name=name,
            last_name=lastname,
            birthdate=bdate,
            email=email,
            phone=phone,
            cpf=cpf,
        )
        try:
            c.full_clean()
        except Exception as exc:
            raise CommandError(f'invalid data: {exc}') from exc

        c.set_password(password)
        c.is_superuser = True
        c.is_staff = True
        c.save()

        self.stdout.write(f'User successfully created: {c.username}')

    @staticmethod
    def input_date():
        """
        Prompts the user for a birth date and converts it to a datetime.date object.

        Raises:
            CommandError: If the date format is invalid.

        Returns:
            datetime.date: The birth date.
        """
        date = input('Birth date (YYYY-MM-DD): ')
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
            return date

        except ValueError as exc:
            raise CommandError(
                'Cannot convert birth date to the valid date format YYYY-MM-DD.'
            ) from exc
