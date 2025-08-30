"""
Tests for the ReservationHistory detail view.
"""

import pytest
from django.urls import reverse

from reservations.models import Reservation


@pytest.mark.django_db
def test_reservation_history_view_uses_correct_template(
    authenticated_client, reservation_history_setup
):
    """Tests if the correct template is rendered."""
    # Arrange
    client, _ = authenticated_client
    _, reservation = reservation_history_setup
    url = reverse('reservation_history', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert 'reservation_history.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reservation_history_view_sends_only_client_reservations_to_context(
    authenticated_client, reservation_history_setup
):
    """
    Tests if only the reservations belonging to the current session's client are added to the context.
    """
    # Arrange
    client, user = authenticated_client
    _, reservation = reservation_history_setup
    reservation.status = 'A'
    reservation.client = user
    reservation.save()

    url = reverse('reservation_history', args=[reservation.pk])
    expected_reservation = Reservation.objects.get(
        pk=reservation.pk, client=user, status__in=['A', 'S', 'C', 'F']
    )

    # Act
    response = client.get(url)
    result_reservation = response.context['reservation']

    # Assert
    assert result_reservation == expected_reservation


@pytest.mark.django_db
def test_reservation_history_view_unauthenticated_user_is_redirected_to_signin(
    client, reservation_history_setup
):
    """
    If the client is not authenticated, they are redirected to signin."""
    # Arrange
    _, reservation = reservation_history_setup
    url = reverse('reservation_history', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    expected_url = reverse('signin') + f'?next={url}'
    assert response.url == expected_url
