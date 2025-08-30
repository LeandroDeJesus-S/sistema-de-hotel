"""
Tests for the reservations tasks.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from ddf import G

from clients.models import Client
from payments.models import Payment
from reservations.models import Reservation, Room
from reservations.tasks import check_reservation_dates, release_room


@pytest.mark.django_db
def test_check_reservation_dates_finalizes_past_reservations(db_setup):
    """
    Tests if the check_reservation_dates function deactivates, finalizes the reservation,
    and releases the room correctly.
    """
    # Arrange
    for r in Reservation.objects.all():
        r.checkout = datetime.now().date() - timedelta(days=1)
        r.active = True
        r.room.available = False
        r.room.save()
        r.save()

    # Act
    check_reservation_dates()

    # Assert
    for r in Reservation.objects.all():
        assert not r.active
        assert r.status == 'F'
        assert r.room.available


@pytest.mark.django_db
def test_release_room_makes_room_available_without_finalized_payment(db_setup):
    """
    Tests if the release_room task correctly releases the room
    if it does not have a finalized payment.
    """
    # Arrange
    # Create a new client and room for this test to ensure unique reservation_id
    client = G(Client)
    room = G(Room)
    reservation = G(
        Reservation,
        client=client,
        room=room,
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
        amount=Decimal('100.00'),
    )

    reservation.room.available = False
    reservation.room.save()
    reservation.save()

    # Act
    release_room(reservation.pk)

    # Assert
    reservation.refresh_from_db()
    assert reservation.room.available


@pytest.mark.django_db
def test_release_room_does_not_free_room_with_finalized_payment(db_setup):
    """
    Tests if the release_room task does not release the room if it has a finalized payment.
    """
    # Arrange
    # Create a new client and room for this test to ensure unique reservation_id
    client = G(Client)
    room = G(Room)
    reservation = G(
        Reservation,
        client=client,
        room=room,
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
        amount=Decimal('100.00'),
    )

    reservation.room.available = False
    reservation.room.save()
    reservation.save()

    Payment.objects.create(reservation=reservation, amount=reservation.amount, status='F')

    # Act
    release_room(reservation.pk)

    # Assert
    reservation.refresh_from_db()
    assert not reservation.room.available


def test_release_room_does_nothing_if_reservation_does_not_exist(mocker):
    """
    Tests if the task does nothing when a non-existent reservation id is passed.
    """
    # Arrange
    mock_get = mocker.patch('reservations.tasks.Reservation.objects.get')
    mock_get.side_effect = Reservation.DoesNotExist

    # Act & Assert
    try:
        release_room(18)
    except Reservation.DoesNotExist:
        pytest.fail('Reservation.DoesNotExist was raised unexpectedly')
