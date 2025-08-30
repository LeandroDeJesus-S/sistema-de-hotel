"""
Tests for the reservations tasks.
"""
from datetime import datetime, timedelta

import pytest
from django.core.management import call_command

from payments.models import Payment
from reservations.models import Reservation
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
    for r in Reservation.objects.all():
        r.room.available = False
        r.room.save()
        r.save()

        # Act
        release_room(r.pk)

        # Assert
        r.refresh_from_db()
        assert r.room.available


@pytest.mark.django_db
def test_release_room_does_not_free_room_with_finalized_payment(db_setup):
    """
    Tests if the release_room task does not release the room if it has a finalized payment.
    """
    # Arrange
    for r in Reservation.objects.all():
        r.room.available = False
        r.room.save()
        r.save()

        Payment.objects.create(reservation=r, amount=r.amount, status='F')

        # Act
        release_room(r.pk)

        # Assert
        r.refresh_from_db()
        assert not r.room.available


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
        pytest.fail("Reservation.DoesNotExist was raised unexpectedly")
