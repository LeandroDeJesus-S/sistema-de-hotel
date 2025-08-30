"""
Configuration for pytest.
"""

import pytest
from django.core.management import call_command


@pytest.fixture
def home_models_db_setup(db):
    """
    Loads the necessary fixtures for the home app model tests.
    """
    call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
    call_command('loaddata', 'tests/fixtures/contato_fixture.json')


@pytest.fixture
def home_views_db_setup(db):
    """
    Loads the necessary fixtures for the home app view tests.
    """
    call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
    call_command('loaddata', 'tests/fixtures/servico_fixture.json')
    call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
    call_command('loaddata', 'tests/fixtures/classe_fixture.json')
    call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
    call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
    call_command('loaddata', 'tests/fixtures/reserva_fixture.json')


@pytest.fixture
def home_response(client, home_views_db_setup):
    """
    Returns the response for the home page.
    """
    return client.get('/')
