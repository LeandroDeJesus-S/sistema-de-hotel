"""
Pytest fixtures for the services app.
"""
import pytest
from ddf import G
from services.models import Service
from home.models import Hotel


@pytest.fixture
def hotel_instance(db):
    """
    Provides a Hotel instance.
    """
    return G(Hotel)

@pytest.fixture
def service_instance(db, hotel_instance):
    """
    Provides a Service instance.
    """
    return G(Service, hotel=hotel_instance)
