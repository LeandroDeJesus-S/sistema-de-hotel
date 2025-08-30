"""
Tests for the Room detail view.
"""
from datetime import datetime, timedelta

import pytest
from django.urls import reverse

from reservations.models import Benefit, Reservation
from clients.models import Client


@pytest.mark.django_db
def test_room_detail_view_uses_correct_template(client, room_view_setup):
    """Tests if room detail view is rendering the correct template."""
    # Arrange
    room = room_view_setup
    url = reverse('room', args=[room.pk])

    # Act
    response = client.get(url)

    # Assert
    assert 'room.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_room_detail_view_sends_correct_room_to_context(client, room_view_setup):
    """
    Tests if the correct room is sent in the context.
    """
    # Arrange
    room = room_view_setup
    url = reverse('room', args=[room.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.context['room'] == room


@pytest.mark.django_db
def test_room_detail_view_benefits_are_sent_to_context(client, room_view_setup):
    """
    Tests if all benefits are sent to the context in room detail view."""
    # Arrange
    room = room_view_setup
    url = reverse('room', args=[room.pk])
    expected_benefits = list(Benefit.objects.all())

    # Act
    response = client.get(url)
    result_benefits = list(response.context['benefits'])

    # Assert
    assert result_benefits == expected_benefits


@pytest.mark.django_db
def test_room_detail_view_reservation_on_not_in_context_for_unauthenticated_user(
    client, room_view_setup
):
    """
    Tests that for an unauthenticated user, 'reservation_on' is not added to the context in room detail view.
    """
    # Arrange
    room = room_view_setup
    url = reverse('room', args=[room.pk])

    # Act
    response = client.get(url)

    # Assert
    assert 'reservation_on' not in response.context


@pytest.mark.django_db
def test_room_detail_view_reservation_on_not_in_context_for_user_with_no_reservations(
    authenticated_client, room_view_setup
):
    """
    Tests that for an authenticated user with no active or scheduled reservations,
    'reservation_on' is not added to the context in room detail view.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    url = reverse('room', args=[room.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.context.get('reservation_on') is None


@pytest.mark.django_db
@pytest.mark.parametrize("status", ['A', 'S'])
def test_room_detail_view_reservation_on_in_context_for_user_with_reservations(
    authenticated_client, room_view_setup, status
):
    """
    Tests that for an authenticated user with active or scheduled reservations,
    'reservation_on' is added to the context in room detail view.
    """
    # Arrange
    client, user = authenticated_client
    room = room_view_setup
    url = reverse('room', args=[room.pk])
    reservation = Reservation.objects.create(
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
        client=user,
        room=room,
        status=status,
    )

    # Act
    response = client.get(url)

    # Assert
    assert response.context['reservation_on'] == reservation