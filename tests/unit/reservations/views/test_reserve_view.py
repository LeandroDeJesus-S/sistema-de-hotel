"""
Tests for the Reserve view.
"""

from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from ddf import G
from django.urls import reverse

from clients.feedback_messages import Recaptcha
from exc import Result
from reservations.feedback_messages import ReservationMessages, ReserveErrorMessages
from reservations.models import Reservation
from reservations.rules import ReserveRules
from utils.supporttest import get_message


@pytest.mark.django_db
def test_reserve_view_uses_correct_template(authenticated_client, room_model):
    """
    Tests if reserve view is rendering the correct template.
    """
    # Arrange
    client, _ = authenticated_client
    url = reverse('reserve', args=[room_model.pk])

    # Act
    response = client.get(url)

    # Assert
    assert 'reserve.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reserve_with_valid_data_redirects_to_checkout(
    mocker, authenticated_client, room_model, mock_recaptcha,
):
    """
    Tests if with valid data it redirects to checkout after reservation is created.
    """
    # Arrange
    client, user = authenticated_client
    url = reverse('reserve', args=[room_model.pk])
    reservation = Reservation(pk=1, client=user, room=room_model)
    mock_initialize = mocker.patch(
        'reservations.views.svc.initialize_reservation',
        return_value=Result.Ok(reservation),
    )
    checkin = datetime.now().date() + timedelta(days=2)
    valid_reserve_data = {
        'checkin': checkin,
        'checkout': checkin + timedelta(days=5),
        'g-recaptcha-response': 'test',
    }

    # Act
    response = client.post(url, valid_reserve_data)

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('checkout', args=[reservation.pk])
    mock_initialize.assert_called_once()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'checkin_date, error_message',
    [
        (
            (datetime.now() - timedelta(days=1)).date(),
            ReserveErrorMessages.INVALID_CHECKIN_DATE,
        ),
        (
            ReserveRules.checkin_anticipation_offset() + timedelta(days=1),
            ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION,
        ),
    ],
)
def test_reserve_with_invalid_checkin_date_renders_reserve_with_message(
    authenticated_client,
    room_model,
    checkin_date,
    mock_recaptcha,
    error_message,
    mocker,
):
    """
    Tests if it renders the reserve page again with the correct message for invalid checkin date.
    """
    # Arrange
    invalid_reservation_data = {
        'checkin': checkin_date,
        'checkout': checkin_date + timedelta(days=5),
        'g-recaptcha-response': 'test',
    }
    client, _ = authenticated_client
    url = reverse('reserve', args=[room_model.pk])

    mocker.patch(
        'reservations.views.svc.initialize_reservation',
        return_value=Result.Err(msg=error_message),
    )

    # Act
    response = client.post(url, invalid_reservation_data)
    message = get_message(response)

    # Assert
    assert message == error_message


@pytest.mark.django_db
@pytest.mark.parametrize('status', ['A', 'S'])
def test_reserve_with_existing_reservation_redirects_to_rooms_with_message(
    authenticated_client, room_model, status
):
    """
    Tests if a client trying to access the reserve page with an active or scheduled reservation
    is redirected to the rooms page with the correct message.
    """
    # Arrange
    client, user = authenticated_client
    url = reverse('reserve', args=[room_model.pk])
    G(
        Reservation,
        client=user,
        room=room_model,
        status=status,
        checkin=datetime.now().date(),
        checkout=datetime.now().date() + timedelta(days=1),
    )

    # Act
    response = client.get(url)
    message = get_message(response)

    # Assert
    assert message == ReservationMessages.ALREADY_HAVE_A_RESERVATION


@pytest.mark.django_db
def test_reserve_unexpected_error_redirects_to_room_with_message(
    mocker, authenticated_client, room_model, mock_recaptcha,
):
    """
    Tests if an unexpected exception occurs when sending form data,
    it redirects to the room page with the correct message.
    """
    # Arrange
    client, _ = authenticated_client
    mocker.patch('reservations.domain.entities.Reservation.safe_create', return_value=Result.Err(
        ReservationMessages.RESERVATION_FAIL
    ))
    url = reverse('reserve', args=[room_model.pk])
    checkin = datetime.now().date() + timedelta(days=2)
    valid_reserve_data = {
        'checkin': checkin,
        'checkout': checkin + timedelta(days=5),
        'g-recaptcha-response': 'test',
    }

    # Act
    response = client.post(url, valid_reserve_data)
    message = get_message(response)

    # Assert
    assert response.status_code == HTTPStatus.FOUND
    assert message == ReservationMessages.RESERVATION_FAIL


@pytest.mark.django_db
def test_reserve_invalid_captcha_redirects_to_reserve_with_message(
    mocker, authenticated_client, room_model
):
    """
    Tests if an invalid captcha redirects back to the reserve page with the correct message.
    """
    # Arrange
    client, _ = authenticated_client
    mocker.patch('reservations.views.support.verify_captcha', return_value=False)
    url = reverse('reserve', args=[room_model.pk])
    checkin = datetime.now().date() + timedelta(days=2)
    valid_reserve_data = {
        'checkin': checkin,
        'checkout': checkin + timedelta(days=5),
        'g-recaptcha-response': 'test',
    }

    # Act
    response = client.post(url, valid_reserve_data)
    message = get_message(response)

    # Assert
    assert message == Recaptcha.INVALID_MESSAGE
