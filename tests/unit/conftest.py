import re

import pytest
from django.core.management import call_command

from clients.models import Client


@pytest.fixture(scope='function', autouse=True)
def auth_backend(settings):
    """Use the custom authentication backend for tests."""
    settings.AUTHENTICATION_BACKENDS = ['clients.authenticator.UserEmailAuthBackend']
    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Load data fixtures for all unit tests."""
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/contato_fixture.json')
        call_command('loaddata', 'tests/fixtures/servico_fixture.json')
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')
        call_command('loaddata', 'tests/fixtures/pagamento_fixture.json')


@pytest.fixture(scope='session', autouse=True)
def faker_session_locale():
    return ['pt_BR']


@pytest.fixture
def valid_client_data(faker):
    """
    Provides a dictionary with valid data for creating a Client instance.
    """
    first_name = re.sub(r'[^a-zA-Z]', '', faker.first_name().split(' ')[0])
    last_name = re.sub(r'[^a-zA-Z]', '', faker.last_name().split(' ')[0])
    return {
        'username': faker.user_name(),
        'password': faker.password(
            length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
        ),
        'first_name': first_name,
        'last_name': last_name,
        'birthdate': faker.date_of_birth(minimum_age=18, maximum_age=80),
        'email': faker.email(),
        'phone': '11999999999',
        'cpf': faker.cpf().replace('.', '').replace('-', ''),
    }


@pytest.fixture(scope='function')
def user(db, valid_client_data, monkeypatch):
    """
    Provides a valid user instance.
    """
    u = Client.objects.create_user(**valid_client_data)
    monkeypatch.setattr(u, 'raw_password', valid_client_data['password'], raising=False)
    return u


@pytest.fixture(scope='function')
def authenticated_client(client, user):
    """
    Logs in a client and returns the client and user.
    """
    client.force_login(user)
    return client, user


@pytest.fixture
def mock_recaptcha(responses):
    responses.add(
        responses.POST,
        'https://www.google.com/recaptcha/api/siteverify',
        json={'success': True, 'score': 0.9},
        status=200,
    )



