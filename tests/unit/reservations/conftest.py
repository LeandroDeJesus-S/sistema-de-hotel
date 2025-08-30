"""
Configuration for pytest.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from ddf import G

from clients.models import Client
from home.models import Hotel
from reservations.models import Class, Reservation, Room


@pytest.fixture
def db_setup(django_db_setup):
    return django_db_setup


@pytest.fixture
def valid_benefit_data():
    """
    Returns a dictionary with valid data to create a Benefit.
    """
    return {
        'name': 'beneficio',
        'short_desc': 'descrição curta',
        'icon': 'test/test_icon.png',
        'displayable_on_homepage': False,
    }


@pytest.fixture
def valid_room_data(db_setup):
    """
    Returns a dictionary with valid data to create a Room.
    """
    return {
        'room_class': Class.objects.first(),
        'number': '202A',
        'adult_capacity': 1,
        'child_capacity': 0,
        'size': 25.5,
        'daily_price': Decimal('100.00'),
        'available': True,
        'image': 'test/room_test.jpg',
        'short_desc': 'desc test',
        'long_desc': None,
        'hotel': Hotel.objects.first(),
    }


@pytest.fixture
def valid_reservation_data(db_setup):
    """
    Returns a dictionary with valid data to create a Reservation.
    """
    client = Client.objects.get(pk=1)
    room = Room.objects.get(pk=1)
    checkin = datetime.now().date()
    checkout = checkin + timedelta(days=5)
    cost = (checkout - checkin).days * room.daily_price_in_cents / 100

    return {
        'client': client,
        'checkin': checkin,
        'checkout': checkout,
        'amount': f'{cost}',
        'observations': '*' * 100,
        'room': room,
    }


@pytest.fixture
def reservation_history_setup(db, user):
    """
    Provides common setup for reservation history view tests.
    """
    reservation = G(Reservation, client=user, status='A', amount=Decimal('500.00'))
    return user, reservation


@pytest.fixture
def reserve_view_setup(db_setup):
    """
    Provides common setup for the reserve view tests.
    """
    user = Client.objects.get(pk=1)
    room = Room.objects.get(pk=1)
    return user, room


@pytest.fixture
def room_view_setup(db_setup):
    """
    Provides common setup for the room view tests.
    """
    room = Room.objects.get(pk=1)
    return room


@pytest.fixture
def rooms_view_setup(db_setup):
    """
    Provides common setup for the rooms view tests.
    """
    rooms = Room.objects.all()
    return rooms


@pytest.fixture
def room1(db_setup):
    """
    Returns a Room instance with pk=1.
    """
    return Room.objects.get(pk=1)


@pytest.fixture
def valid_reserve_data():
    """
    Returns a dictionary with valid data for the reserve form.
    """
    return {
        'checkin': datetime.now().strftime('%Y-%m-%d'),
        'checkout': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
        'obs': '',
    }


@pytest.fixture
def reservations_setup(db_setup):
    """
    Provides common setup for reservation-related tests.
    """
    # This fixture is intended to provide a Reservation object for tests.
    # The actual data loaded by db_setup should ensure a Reservation exists.
    return Reservation.objects.get(pk=1)
