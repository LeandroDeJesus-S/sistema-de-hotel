"""
Tests for the Rooms view.
"""

from datetime import datetime, timedelta

import pytest
from ddf import G
from django.urls import reverse

from exc import Result
from reservations.application.services import ReservationService
from reservations.models import Reservation, Room


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
def test_rooms_view_reservation_on_not_in_context_for_unauthenticated_user(
    mocker, client, reservations_container
):
    """
    Tests that for an unauthenticated user, 'reservation_on' is not added to the context in rooms view.
    """
    # Arrange
    url = reverse('rooms')
    G(Room)
    svc_mock = mocker.MagicMock(spec=ReservationService, room_repo=mocker.MagicMock())
    svc_mock.room_repo.fetch_all.return_value = Result.Ok([])
    svc_mock.room_repo.fetch_all_benefits.return_value = Result.Ok([])
    svc_mock.room_repo.fetch_all.return_value = Result.Ok([])

    # Act
    with reservations_container.reservation_service.override(svc_mock):
        response = client.get(url)

    # Assert
    assert 'reservation_on' not in response.context


@pytest.mark.django_db
def test_rooms_view_reservation_on_not_in_context_for_user_with_no_reservations(
    mocker, authenticated_client, reservations_container
):
    """
    Tests that for an authenticated user with no active or scheduled reservations,
    'reservation_on' is not added to the context in rooms view.
    """
    # Arrange
    client, _ = authenticated_client
    url = reverse('rooms')
    G(Room)
    svc_mock = mocker.MagicMock(spec=ReservationService, room_repo=mocker.MagicMock())
    svc_mock.room_repo.fetch_all.return_value = Result.Ok([])
    svc_mock.room_repo.fetch_all_benefits.return_value = Result.Ok([])
    svc_mock.room_repo.fetch_all.return_value = Result.Ok([])
    svc_mock.fetch_client_active_reservations.return_value = Result.Ok([])

    # Act
    with reservations_container.reservation_service.override(svc_mock):
        response = client.get(url)

    # Assert
    assert response.context['reservation_on'] == []


@pytest.mark.django_db
@pytest.mark.parametrize('status', ['A', 'S'])
def test_rooms_view_reservation_on_in_context_for_user_with_reservations(
    mocker, authenticated_client, room_model, status, reservations_container
):
    """
    Tests that for an authenticated user with active or scheduled reservations,
    'reservation_on' is added to the context in rooms view.
    """
    # Arrange
    client, user = authenticated_client
    url = reverse('rooms')
    reservation = G(
        Reservation,
        client=user,
        room=room_model,
        status=status,
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
    )
    svc_mock = mocker.MagicMock(spec=ReservationService, room_repo=mocker.MagicMock())
    svc_mock.room_repo.fetch_all.return_value = Result.Ok([])
    svc_mock.room_repo.fetch_all_benefits.return_value = Result.Ok([])
    svc_mock.fetch_client_active_reservations.return_value = Result.Ok([reservation])

    # Act
    with reservations_container.reservation_service.override(svc_mock):
        response = client.get(url)

    # Assert
    assert response.context['reservation_on'] == [reservation]
