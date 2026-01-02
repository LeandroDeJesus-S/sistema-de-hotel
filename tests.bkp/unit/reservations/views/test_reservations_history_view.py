"""
Tests for the ReservationsHistory view.
"""

import pytest
from django.urls import reverse

from reservations.models import Reservation


@pytest.mark.django_db
def test_reservations_history_view_uses_correct_template(authenticated_client):
    """Tests if the correct template is being used."""
    # Arrange
    client, _ = authenticated_client
    url = reverse('reservations_history')

    # Act
    response = client.get(url)

    # Assert
    assert 'reservations_history.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reservations_history_view_sends_user_reservations_to_context(
    authenticated_client,
):
    """
    Tests if the logged-in user has access to their reservations."""
    # Arrange
    client, user = authenticated_client
    url = reverse('reservations_history')
    expected_reservations = Reservation.objects.filter(
        client=user, status__in=['A', 'S', 'C', 'F']
    ).order_by('-id')

    # Act
    response = client.get(url)
    result_reservations = response.context['reservations']

    # Assert
    assert list(result_reservations) == list(expected_reservations)


@pytest.mark.django_db
def test_reservations_history_view_unauthenticated_user_is_redirected_to_signin(client):
    """
    Tests if the client is not logged in, they are redirected to signin."""
    # Arrange
    url = reverse('reservations_history')

    # Act
    response = client.get(url)

    # Assert
    expected_url = reverse('signin') + f'?next={url}'
    assert response.url == expected_url
