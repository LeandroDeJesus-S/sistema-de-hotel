"""
Tests for the Reserve view.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django_q.models import Schedule

from reservations.models import Reservation
from utils.supportmodels import ReserveErrorMessages, ReserveRules
from utils.supporttest import get_message
from utils.supportviews import INVALID_RECAPTCHA_MESSAGE, ReserveMessages


@pytest.mark.django_db
def test_reserve_view_uses_correct_template(
    authenticated_client, room_view_setup
):
    """
    Tests if reserve view is rendering the correct template.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    url = reverse('reserve', args=[room.pk])

    # Act
    response = client.get(url)

    # Assert
    assert 'reserve.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reserve_with_valid_data_redirects_to_checkout(
    mocker, authenticated_client, room_view_setup, valid_reserve_data
):
    """
    Tests if with valid data it redirects to checkout after reservation is created.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=True)
    url = reverse('reserve', args=[room.pk])

    # Act
    response = client.post(url, valid_reserve_data)

    # Assert
    last_reservation = Reservation.objects.last()
    assert response.url == reverse('checkout', args=[last_reservation.pk])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "checkin_date, error_message",
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
    mocker,
    authenticated_client,
    room_view_setup,
    valid_reserve_data,
    checkin_date,
    error_message,
):
    """
    Tests if it renders the reserve page again with the correct message for invalid checkin date.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=True)
    url = reverse('reserve', args=[room.pk])
    valid_reserve_data['checkin'] = checkin_date
    if error_message == ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION:
        valid_reserve_data['checkout'] = checkin_date + timedelta(days=1)

    # Act
    response = client.post(url, valid_reserve_data)
    message = get_message(response)

    # Assert
    assert message == error_message


@pytest.mark.django_db
def test_reserve_associates_client_with_reservation(
    mocker, authenticated_client, room_view_setup, valid_reserve_data
):
    """
    Tests if the client is correctly associated with the reservation.
    """
    # Arrange
    client, user = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=True)
    url = reverse('reserve', args=[room.pk])

    # Act
    client.post(url, valid_reserve_data)
    last_reservation = Reservation.objects.last()

    # Assert
    assert last_reservation.client == user


@pytest.mark.django_db
def test_reserve_associates_room_with_reservation(
    mocker, authenticated_client, room_view_setup, valid_reserve_data
):
    """
    Tests if the room is correctly associated with the reservation.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=True)
    url = reverse('reserve', args=[room.pk])

    # Act
    client.post(url, valid_reserve_data)
    last_reservation = Reservation.objects.last()

    # Assert
    assert last_reservation.room == room


@pytest.mark.django_db
def test_reserve_calculates_cost_correctly(
    mocker, authenticated_client, room_view_setup, valid_reserve_data
):
    """
    Tests if the reservation cost is calculated and added correctly.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=True)
    url = reverse('reserve', args=[room.pk])

    # Act
    client.post(url, valid_reserve_data)
    last_reservation = Reservation.objects.last()

    # Assert
    expected_amount = (
        Decimal(str(last_reservation.reservation_days)) * room.daily_price
    )
    assert last_reservation.amount == expected_amount


@pytest.mark.django_db
def test_reserve_creates_django_q_schedule(
    mocker, authenticated_client, room_view_setup, valid_reserve_data
):
    """
    Tests if the Schedule to release the room is created correctly.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=True)
    url = reverse('reserve', args=[room.pk])

    # Act
    client.post(url, valid_reserve_data)
    last_schedule = Schedule.objects.last()

    # Assert
    assert last_schedule.func == 'reservations.tasks.release_room'


@pytest.mark.django_db
@pytest.mark.parametrize("status", ['A', 'S'])
def test_reserve_with_existing_reservation_redirects_to_rooms_with_message(
    authenticated_client, room_view_setup, status
):
    """
    Tests if a client trying to access the reserve page with an active or scheduled reservation
    is redirected to the rooms page with the correct message.
    """
    # Arrange
    client, user = authenticated_client
    room = room_view_setup
    url = reverse('reserve', args=[room.pk])
    Reservation.objects.create(
        client=user,
        room=room,
        checkin=datetime.now().date(),
        checkout=(datetime.now() + timedelta(days=5)).date(),
        status=status,
        amount=Decimal('500.00')
    )

    # Act
    response = client.get(url)
    message = get_message(response)

    # Assert
    assert message == ReserveMessages.ALREADY_HAVE_A_RESERVATION


@pytest.mark.django_db
def test_reserve_unexpected_error_redirects_to_room_with_message(
    mocker, authenticated_client, room_view_setup, valid_reserve_data
):
    """
    Tests if an unexpected exception occurs when sending form data,
    it redirects to the room page with the correct message.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=True)
    mocker.patch('reservations.views.convert_date', side_effect=Exception)
    url = reverse('reserve', args=[room.pk])

    # Act
    response = client.post(url, valid_reserve_data)
    message = get_message(response)

    # Assert
    assert message == ReserveMessages.RESERVATION_FAIL


@pytest.mark.django_db
def test_reserve_invalid_captcha_redirects_to_reserve_with_message(
    mocker, authenticated_client, room_view_setup, valid_reserve_data
):
    """
    Tests if an invalid captcha redirects back to the reserve page with the correct message.
    """
    # Arrange
    client, _ = authenticated_client
    room = room_view_setup
    mocker.patch('reservations.views.support.verify_captcha', return_value=False)
    url = reverse('reserve', args=[room.pk])

    # Act
    response = client.post(url, valid_reserve_data)
    message = get_message(response)

    # Assert
    assert message == INVALID_RECAPTCHA_MESSAGE