"""
Tests for the Rooms view.
"""

from datetime import datetime, timedelta
import pytest
from ddf import G
from django.urls import reverse

from exc import Result
from reservations.models import Benefit, Reservation, Room


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
def test_rooms_view_sends_all_rooms_to_context_ordered_by_price(mocker, client):
    """
    Tests if all rooms are passed to the context ordered by daily_price descending.
    """
    # Arrange
    url = reverse('rooms')
    G(Room, n=3)
    room = Room.objects.first()
    room.available = False
    room.save()
    expected_rooms = list(Room.objects.all().order_by('-daily_price'))
    mocker.patch(
        'reservations.views.svc.room_repo.fetch_all',
        return_value=Result(value=expected_rooms, error=None),
    )

    # Act
    response = client.get(url)
    result_rooms = response.context['rooms']

    # Assert
    assert len(result_rooms) == len(expected_rooms)
    assert [r.id for r in result_rooms] == [r.id for r in expected_rooms]


@pytest.mark.django_db
def test_rooms_view_benefits_are_sent_to_context(authenticated_client, mocker):
    """
    Tests if all benefits are sent to the context in rooms view.
    """
    # Arrange
    client, _ = authenticated_client
    url = reverse('rooms')
    benefits = G(Benefit, n=3)
    expected_benefits = list(benefits)
    mocker.patch(
        'reservations.views.svc.room_repo.fetch_all_benefits',
        return_value=type('Result', (), {'value': expected_benefits, 'error': None})(),
    )

    # Act
    response = client.get(url)
    result_benefits = response.context.get('benefits')

    # Assert
    assert 'benefits' in response.context, f'context {response.context}'
    assert list(result_benefits) == expected_benefits


@pytest.mark.django_db
def test_rooms_view_reservation_on_not_in_context_for_unauthenticated_user(
    mocker, client
):
    """
    Tests that for an unauthenticated user, 'reservation_on' is not added to the context in rooms view.
    """
    # Arrange
    url = reverse('rooms')
    G(Room)
    mocker.patch(
        'reservations.views.svc.room_repo.fetch_all_benefits',
        return_value=Result(value=[], error=None),
    )
    mocker.patch(
        'reservations.views.svc.room_repo.fetch_all',
        return_value=Result(value=list(Room.objects.all()), error=None),
    )

    # Act
    response = client.get(url)

    # Assert
    assert 'reservation_on' not in response.context


@pytest.mark.django_db
def test_rooms_view_reservation_on_not_in_context_for_user_with_no_reservations(
    mocker, authenticated_client
):
    """
    Tests that for an authenticated user with no active or scheduled reservations,
    'reservation_on' is not added to the context in rooms view.
    """
    # Arrange
    client, _ = authenticated_client
    url = reverse('rooms')
    G(Room)
    mocker.patch(
        'reservations.views.svc.room_repo.fetch_all_benefits',
        return_value=Result(value=[], error=None),
    )
    mocker.patch(
        'reservations.views.svc.room_repo.fetch_all',
        return_value=Result(value=list(Room.objects.all()), error=None),
    )
    mocker.patch(
        'reservations.views.svc.fetch_client_active_reservations',
        return_value=([], None),
    )

    # Act
    response = client.get(url)

    # Assert
    assert response.context['reservation_on'] == []


@pytest.mark.django_db
@pytest.mark.parametrize('status', ['A', 'S'])
def test_rooms_view_reservation_on_in_context_for_user_with_reservations(
    mocker, authenticated_client, room_model, status
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
    mocker.patch(
        'reservations.views.svc.room_repo.fetch_all_benefits',
        return_value=Result(value=[], error=None),
    )
    mocker.patch(
        'reservations.views.svc.fetch_client_active_reservations',
        return_value=([reservation], None),
    )

    # Act
    response = client.get(url)

    # Assert
    assert response.context['reservation_on'] == [reservation]
