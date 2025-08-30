"""
Tests for the Rooms view.
"""
from datetime import datetime, timedelta

import pytest
from django.urls import reverse

from reservations.models import Benefit, Reservation, Room
from clients.models import Client


@pytest.mark.django_db
def test_rooms_view_uses_correct_template(client):
    """Tests if rooms view is rendering the correct template."""
    # Arrange
    url = reverse('rooms')

    # Act
    response = client.get(url)

    # Assert
    assert 'rooms.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_rooms_view_sends_all_rooms_to_context_ordered_by_price(client):
    """
    Tests if all rooms are passed to the context ordered by daily_price descending.
    """
    # Arrange
    url = reverse('rooms')
    room = Room.objects.get(pk=2)
    room.available = False
    room.save()
    expected_rooms = list(Room.objects.all().order_by('-daily_price'))

    # Act
    response = client.get(url)
    result_rooms = list(response.context['rooms'])

    # Assert
    assert result_rooms == expected_rooms


@pytest.mark.django_db
def test_rooms_view_benefits_are_sent_to_context(client):
    """
    Tests if all benefits are sent to the context in rooms view."""
    # Arrange
    url = reverse('rooms')
    expected_benefits = list(Benefit.objects.all())

    # Act
    response = client.get(url)
    result_benefits = list(response.context['benefits'])

    # Assert
    assert result_benefits == expected_benefits


@pytest.mark.django_db
def test_rooms_view_reservation_on_not_in_context_for_unauthenticated_user(client):
    """
    Tests that for an unauthenticated user, 'reservation_on' is not added to the context in rooms view.
    """
    # Arrange
    url = reverse('rooms')

    # Act
    response = client.get(url)

    # Assert
    assert 'reservation_on' not in response.context


@pytest.mark.django_db
def test_rooms_view_reservation_on_not_in_context_for_user_with_no_reservations(
    authenticated_client
):
    """
    Tests that for an authenticated user with no active or scheduled reservations,
    'reservation_on' is not added to the context in rooms view.
    """
    # Arrange
    client, _ = authenticated_client
    url = reverse('rooms')

    # Act
    response = client.get(url)

    # Assert
    assert response.context.get('reservation_on') is None


@pytest.mark.django_db
@pytest.mark.parametrize("status", ['A', 'S'])
def test_rooms_view_reservation_on_in_context_for_user_with_reservations(
    authenticated_client, room1, status
):
    """
    Tests that for an authenticated user with active or scheduled reservations,
    'reservation_on' is added to the context in rooms view.
    """
    # Arrange
    client, user = authenticated_client
    url = reverse('rooms')
    reservation = Reservation.objects.create(
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
        client=user,
        room=room1,
        status=status,
    )

    # Act
    response = client.get(url)

    # Assert
    assert response.context['reservation_on'] == reservation
