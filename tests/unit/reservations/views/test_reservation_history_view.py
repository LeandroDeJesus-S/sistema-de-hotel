"""
Tests for the ReservationHistory detail view.
"""

import pytest
from django.urls import reverse

from reservations.models import Reservation


@pytest.mark.django_db
def test_reservation_history_view_uses_correct_template(
    mocker, authenticated_client, reservation_model
):
    """Tests if the correct template is rendered."""
    # Arrange
    client, _ = authenticated_client
    url = reverse('reservation_history', args=[reservation_model.pk])
    mocker.patch(
        'reservations.views.svc.fetch_reservation_detail', return_value=(reservation_model, None)
    )

    # Act
    response = client.get(url)

    # Assert
    assert 'reservation_history.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reservation_history_view_sends_only_client_reservations_to_context(
    mocker, authenticated_client, reservation_model
):
    """
    Tests if only the reservations belonging to the current session's client are added to the context.
    """
    # Arrange
    client, user = authenticated_client
    reservation_model.client = user
    reservation_model.save()

    url = reverse('reservation_history', args=[reservation_model.pk])
    expected_reservation = reservation_model.pk
    mocker.patch(
        'reservations.views.svc.fetch_reservation_detail',
        return_value=(expected_reservation, None),
    )

    # Act
    response = client.get(url)
    result_reservation = response.context['reservation']

    # Assert
    assert result_reservation == expected_reservation


@pytest.mark.django_db
def test_reservation_history_view_unauthenticated_user_is_redirected_to_signin(
    client, reservation_model
):
    """
    If the client is not authenticated, they are redirected to signin."""
    # Arrange
    url = reverse('reservation_history', args=[reservation_model.pk])

    # Act
    response = client.get(url)

    # Assert
    expected_url = reverse('signin') + f'?next={url}'
    assert response.url == expected_url
