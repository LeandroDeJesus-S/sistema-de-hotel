from typing import Any
from django.core.management.base import BaseCommand, CommandError
from getpass import getpass
from datetime import datetime
from clients.models import Client


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            self.program(*args, **options)
        except KeyboardInterrupt:
            self.stderr.write('command stopped')

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
            
        
        c = Client.objects.create(
            username=username,
            password=password,
            first_name=name,
            last_name=lastname,
            birthdate=bdate,
            email=email,
            phone=phone,
            cpf=cpf
        )
        self.stdout.write(f'created: {c.pk}')

    
    @staticmethod
    def input_date():
        date = input('birth date (yyy-mm-dd): ')
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
            return date

        except ValueError as exc:
            raise CommandError('cannot convert birth date to the valid date format yyy-mm-dd') from exc

