import pytest
from django.core.management import call_command
from ddf import G
from clients.models import Client


@pytest.fixture(scope='function', autouse=True)
def auth_backend(settings):
    """Use the custom authentication backend for tests."""
    settings.AUTHENTICATION_BACKENDS = ['clients.authenticator.UserEmailAuthBackend']
    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


@pytest.fixture(scope='function')
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


@pytest.fixture(scope='session', autouse=True)
def faker_session_locale():
    return ['pt_BR']


@pytest.fixture
def user(db):
    return G(Client)

@pytest.fixture(scope='function')
def authenticated_client(client, user):
    """
    Logs in a client and returns the client and user.
    """
    client.force_login(user)
    return client, user