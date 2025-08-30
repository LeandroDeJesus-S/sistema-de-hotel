"""
Configuration for pytest.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from clients.models import Client
from payments.models import Payment
from reservations.models import Reservation, Room


@pytest.fixture
def db_setup(django_db_setup):
    return django_db_setup


@pytest.fixture
def payment_data(db_setup):
    """
    Returns a dictionary with common data for the tests.
    """
    user = Client.objects.get(pk=1)
    room = Room.objects.get(pk=1)
    checkin = datetime.now().date()
    checkout = checkin + timedelta(days=5)
    amount = (checkout - checkin).days * room.daily_price_in_cents / 100

    reservation = Reservation.objects.create(
        client=user,
        checkin=checkin,
        checkout=checkout,
        amount=Decimal(str(amount)),
        observations='*' * 100,
        room=room,
    )
    payment = Payment.objects.create(reservation=reservation, amount=reservation.amount)
    return {'user': user, 'room': room, 'reservation': reservation, 'payment': payment}


@pytest.fixture
def view_setup(db_setup):
    """
    Provides common setup for the view tests.
    """
    user = Client.objects.get(pk=1)
    user2 = Client.objects.get(pk=2)
    room = Room.objects.get(pk=1)
    room2 = Room.objects.get(pk=2)
    checkin = datetime.now().date()
    checkout = checkin + timedelta(days=5)
    cost = (checkout - checkin).days * room.daily_price_in_cents / 100
    cost2 = (checkout - checkin).days * room2.daily_price_in_cents / 100

    reservation = Reservation.objects.create(
        client=user,
        checkin=checkin,
        checkout=checkout,
        amount=Decimal(str(cost)),
        observations='*' * 100,
        room=room,
    )
    reservation2 = Reservation.objects.create(
        client=user2,
        checkin=checkin,
        checkout=checkout,
        amount=Decimal(str(cost2)),
        observations='*' * 100,
        room=room2,
    )
    return user, user2, reservation, reservation2


@pytest.fixture
def success_view_setup(view_setup):
    """
    Provides common setup for the PaymentSuccess view tests.
    """
    user, user2, reservation, reservation2 = view_setup
    payment = Payment.objects.create(
        reservation=reservation, status='P', amount=reservation.amount
    )
    return user, user2, reservation, reservation2, payment


@pytest.fixture
def cancel_view_setup(view_setup):
    """
    Provides common setup for the PaymentCancel view tests.
    """
    user, user2, reservation, reservation2 = view_setup
    payment = Payment.objects.create(
        reservation=reservation, status='P', amount=reservation.amount
    )
    Payment.objects.create(reservation=reservation2, status='P', amount=reservation2.amount)
    return user, user2, reservation, reservation2, payment
