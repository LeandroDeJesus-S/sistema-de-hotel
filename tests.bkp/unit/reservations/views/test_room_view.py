"""
Tests for the Room detail view.
"""

from datetime import datetime, timedelta

import pytest
from ddf import G
from django.urls import reverse

from exc import Result
from reservations.application.services import ReservationService
from reservations.domain.entities import Benefit as BenefitEntity
from reservations.models import Benefit, Reservation
from utils.support import models_to_entities


@pytest.mark.django_db
def test_room_detail_view_uses_correct_template(client, room_model):
    """Tests if room detail view is rendering the correct template."""
    # Arrange
    url = reverse('room', args=[room_model.pk])

    # Act
    response = client.get(url)

    # Assert
    assert 'room.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_room_detail_view_sends_correct_room_to_context(client, room_model):
    """
    Tests if the correct room is sent in the context.
    """
    # Arrange
    url = reverse('room', args=[room_model.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.context['room'] == room_model


@pytest.mark.django_db
def test_room_detail_view_benefits_are_sent_to_context(authenticated_client, room_model):
    """
    Tests if all benefits are sent to the context in room detail view."""
    # Arrange
    client, _ = authenticated_client
    G(Benefit, n=3)
    url = reverse('room', args=[room_model.pk])
    expected_benefits = models_to_entities(Benefit.objects.all(), BenefitEntity).unwrap()

    # Act
    response = client.get(url)
    result_benefits = response.context['benefits']

    # Assert
    assert result_benefits == expected_benefits


@pytest.mark.django_db
def test_room_detail_view_reservation_on_not_in_context_for_unauthenticated_user(
    mocker, client, room_model, reservations_container
):
    """
    Tests that for an unauthenticated user, 'reservation_on' is not added to the context in room detail view.
    """
    # Arrange
    url = reverse('room', args=[room_model.pk])
    svc_mock = mocker.MagicMock(spec=ReservationService, room_repo=mocker.MagicMock())
    svc_mock.room_repo.fetch_all_benefits.return_value = Result.Ok([])

    # Act
    with reservations_container.reservation_service.override(svc_mock):
        response = client.get(url)

    # Assert
    assert 'reservation_on' not in response.context


@pytest.mark.django_db
def test_room_detail_view_reservation_on_not_in_context_for_user_with_no_reservations(
    mocker, authenticated_client, room_model, reservations_container
):
    """
    Tests that for an authenticated user with no active or scheduled reservations,
    'reservation_on' is not added to the context in room detail view.
    """
    # Arrange
    client, _ = authenticated_client
    url = reverse('room', args=[room_model.pk])
    svc_mock = mocker.MagicMock(spec=ReservationService, room_repo=mocker.MagicMock())
    svc_mock.room_repo.fetch_all_benefits.return_value = Result.Ok([])
    svc_mock.fetch_client_active_reservations.return_value = Result.Ok([])

    # Act
    with reservations_container.reservation_service.override(svc_mock):
        response = client.get(url)

    # Assert
    assert response.context.get('reservation_on') == []


@pytest.mark.django_db
@pytest.mark.parametrize('status', ['A', 'S'])
def test_room_detail_view_reservation_on_in_context_for_user_with_reservations(
    mocker, authenticated_client, room_model, status, reservations_container
):
    """
    Tests that for an authenticated user with active or scheduled reservations,
    'reservation_on' is added to the context in room detail view.
    """
    # Arrange
    client, user = authenticated_client
    url = reverse('room', args=[room_model.pk])
    reservation = G(
        Reservation,
        client=user,
        room=room_model,
        status=status,
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
    )
    svc_mock = mocker.MagicMock(spec=ReservationService, room_repo=mocker.MagicMock())
    svc_mock.room_repo.fetch_all_benefits.return_value = Result.Ok([])
    svc_mock.fetch_client_active_reservations.return_value = Result.Ok([reservation])

    # Act
    with reservations_container.reservation_service.override(svc_mock):
        response = client.get(url)

    # Assert
    assert response.context.get('reservation_on') == [reservation]
