from datetime import datetime
from getpass import getpass
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from clients.models import Client


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            self.program(*args, **options)
        except KeyboardInterrupt:
            self.stderr.write('command stopped')
        return None

    def program(self, *args, **options):
        self.stdout.write('Pass the requested informations')

        username = input('username: ').strip()
        password = getpass().strip()
        pass_confirm = getpass('confirm password:').strip()

        name = input('name: ').strip()
        lastname = input('lastname: ').strip()
        bdate = self.input_date()
        email = input('email: ').strip()
        phone = input('phone: ').strip()
        cpf = input('cpf: ').strip()

        if password != pass_confirm:
            raise CommandError('passwords do not match')

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

        self.stdout.write(f'user successfully created: {c.username}')

    @staticmethod
    def input_date():
        date = input('birth date (yyy-mm-dd): ')
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
            return date

        except ValueError as exc:
            raise CommandError(
                'cannot convert birth date to the valid date format yyy-mm-dd'
            ) from exc
