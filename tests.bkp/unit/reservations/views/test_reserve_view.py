"""
Tests for the Reserve view.
"""

from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from ddf import G
from django.urls import reverse

from base.dtos import MessageDTO, RedirectResultDTO
from clients.feedback_messages import Recaptcha
from exc import Result
from reservations.application.services import ReservationService
from reservations.domain.repo import AbsRoomRepository
from reservations.feedback_messages import ReservationMessages, ReserveErrorMessages
from reservations.models import Reservation
from reservations.rules import ReserveRules
from utils.supporttest import get_message


@pytest.mark.django_db
def test_reserve_view_uses_correct_template(client, room_model, client_model_factory):
    """
    Tests if reserve view is rendering the correct template.
    """
    # Arrange
    customer = client_model_factory()
    client.force_login(customer)

    url = reverse('reserve', args=[room_model.pk])

    # Act
    response = client.get(url)

    # Assert
    assert 'reserve.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reserve_with_valid_data_redirects_to_checkout(
    mocker, authenticated_client, room_model, mock_recaptcha, reservations_container
):
    """
    Tests if with valid data it redirects to checkout after reservation is created.
    """
    # Arrange
    client, user = authenticated_client
    url = reverse('reserve', args=[room_model.pk])
    reservation = Reservation(pk=1, client=user, room=room_model)
    svc_mock = mocker.MagicMock()
    svc_mock.create_reservation.return_value = Result.Ok(
        RedirectResultDTO(url='checkout', args=(reservation.pk,))
    )
    checkin = datetime.now().date() + timedelta(days=2)
    valid_reserve_data = {
        'checkin': checkin,
        'checkout': checkin + timedelta(days=5),
        'g-recaptcha-response': 'test',
    }

    # Act
    with reservations_container.reservation_service.override(svc_mock):
        response = client.post(url, valid_reserve_data)

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('checkout', args=[reservation.pk])


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
    reservations_container,
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
    svc_mock = mocker.MagicMock(spec=ReservationService)
    svc_mock.create_reservation.return_value = Result.Ok(
        RedirectResultDTO(
            url='reserve',
            args=(room_model.pk,),
            messages=[MessageDTO(typ='error', msg=str(error_message))],
        )
    )
    room_repo_mock = mocker.MagicMock(spec=AbsRoomRepository)
    room_repo_mock.fetch_all_classes.return_value = Result.Ok([])

    # Act
    with (reservations_container.reservation_service.override(svc_mock),
        reservations_container.room_repo.override(room_repo_mock)):
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
    mocker,
    authenticated_client,
    room_model,
    mock_recaptcha,
    reservations_container,
):
    """
    Tests if an unexpected exception occurs when sending form data,
    it redirects to the room page with the correct message.
    """
    # Arrange
    client, _ = authenticated_client
    svc_mock = mocker.MagicMock()
    svc_mock.create_reservation.return_value = Result.Ok(
        RedirectResultDTO(
            url='reserve',
            args=(room_model.pk,),
            messages=[MessageDTO(typ='error', msg=str(ReservationMessages.RESERVATION_FAIL))],
        )
    )
    url = reverse('reserve', args=[room_model.pk])
    checkin = datetime.now().date() + timedelta(days=2)
    valid_reserve_data = {
        'checkin': checkin,
        'checkout': checkin + timedelta(days=5),
        'g-recaptcha-response': 'test',
    }

    # Act
    with reservations_container.reservation_service.override(svc_mock):
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
