from datetime import date, timedelta
from decimal import Decimal

import pytest
from ddf import G
from django.contrib.messages.storage.fallback import FallbackStorage

from clients.models import Client
from home.models import Hotel
from payments.models import Payment
from reservations.models import Benefit, Class, Reservation, Room
from schedules.models import Scheduling


@pytest.fixture
def hotel_fixture():
    """
    Fixture to create a Hotel instance.
    """
    return G(Hotel)


@pytest.fixture
def room_class_fixture():
    """
    Fixture to create a Class instance for a room.
    """
    return G(Class)


@pytest.fixture
def benefit_fixture():
    """
    Fixture to create a Benefit instance for a room.
    """
    return G(Benefit)


@pytest.fixture
def room_fixture(room_class_fixture, benefit_fixture, hotel_fixture):
    """
    Fixture to create a Room instance with associated class, benefit, and hotel.
    Set a daily_price that ensures reservation amount is valid.
    """
    room = G(
        Room, room_class=room_class_fixture, hotel=hotel_fixture, daily_price=Decimal('200.00')
    )  # Use Decimal
    room.benefits.add(benefit_fixture)
    return room


@pytest.fixture
def client_fixture():
    """
    Fixture to create a Client instance.
    """
    return G(Client)


@pytest.fixture
def reservation_fixture(client_fixture, room_fixture):
    """
    Fixture to create a Reservation instance.
    """
    checkin = date.today() + timedelta(days=10)
    checkout = checkin + timedelta(days=15)  # Example: 5 days reservation
    reservation = G(
        Reservation,
        client=client_fixture,
        room=room_fixture,
        checkin=checkin,
        checkout=checkout,
        status='I',
    )
    # Calculate and set the amount
    reservation.amount = reservation.calc_reservation_value()
    reservation.save()  # Save after setting amount
    return reservation


@pytest.fixture
def payment_fixture(client_fixture, room_fixture):
    """
    Fixture to create a Payment instance.
    """
    # First, create a reservation with a calculated amount for the client_fixture
    checkin = date.today() + timedelta(days=10)
    checkout = checkin + timedelta(days=15)  # Example: 5 days reservation
    reservation = G(
        Reservation,
        client=client_fixture,
        room=room_fixture,
        checkin=checkin,
        checkout=checkout,
        status='I',
    )
    # Calculate and set the amount
    reservation.amount = reservation.calc_reservation_value()
    reservation.save()  # Save after setting amount

    # Create a Scheduling object for this reservation, as the view expects it
    G(Scheduling, client=client_fixture, reservation=reservation)

    return G(Payment, reservation=reservation, status='P', amount=reservation.amount)


@pytest.fixture
def scheduling_fixture(client_fixture, reservation_fixture):
    """
    Fixture to create a Scheduling instance.
    """
    return G(Scheduling, client=client_fixture, reservation=reservation_fixture)


@pytest.fixture
def client_logged_in(client, client_fixture):
    """
    Fixture to provide a logged-in Django test client.
    """
    client.force_login(client_fixture)
    return client


@pytest.fixture
def schedule_form_data():
    """
    Fixture to provide common form data for scheduling tests.
    """
    return {
        'checkin': (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
        'checkout': (date.today() + timedelta(days=2)).strftime('%Y-%m-%d'),
        'obs': '',
    }


@pytest.fixture
def get_message():
    """
    Helper fixture to extract messages from Django's messages framework.
    Handles both direct responses and messages stored in the session (for redirects).
    """

    def _get_message(response):
        # For direct responses, messages are in context
        if response.context and 'messages' in response.context:
            messages = list(response.context['messages'])
            return messages[0].message if messages else ''
        # For redirects, messages are in the session
        elif hasattr(response, 'wsgi_request') and hasattr(response.wsgi_request, 'session'):
            # Manually load messages from the session
            storage = FallbackStorage(response.wsgi_request)
            messages = list(storage)
            return messages[0].message if messages else ''
        return ''

    return _get_message


@pytest.fixture
def active_room_fixture(room_fixture, client_fixture):
    """
    Fixture to ensure a room has an active reservation, making it "occupied".
    """
    G(
        Reservation,
        client=client_fixture,
        room=room_fixture,
        checkin=date.today() + timedelta(days=5),
        checkout=date.today() + timedelta(days=10),
        status='A',
    )
    return room_fixture
