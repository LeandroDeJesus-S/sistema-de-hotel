from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.urls import reverse
from django_q.tasks import Schedule

from schedules.models import Scheduling
from utils.supportmodels import ReserveErrorMessages
from utils.supportviews import INVALID_RECAPTCHA_MESSAGE, CheckoutMessages


@pytest.mark.django_db
def test_template_used(client_logged_in, room_fixture):
    """
    Verify that the correct template is used for the schedule view.
    """
    url = reverse('schedule', args=[room_fixture.pk])
    response = client_logged_in.get(url)
    assert response.status_code == 200
    assert 'schedule.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_unauthenticated_client_redirected_to_signin(client, room_fixture):
    """
    Verify that an unauthenticated client is redirected to the signin page for the schedule view.
    """
    url = reverse('schedule', args=[room_fixture.pk])
    response = client.get(url)
    expected_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == expected_url


@pytest.mark.django_db
def test_room_pk_passed_to_context(client_logged_in, room_fixture):
    """
    Test if the room primary key is sent to the context.
    """
    url = reverse('schedule', args=[room_fixture.pk])
    response = client_logged_in.get(url)
    assert response.status_code == 200
    assert response.context.get('room_pk') == room_fixture.pk


@pytest.mark.django_db
def test_scheduling_created_if_form_is_valid(
    mocker, client_logged_in, client_fixture, active_room_fixture, schedule_form_data
):
    """
    Scheduling is created if the submitted data is valid.
    """
    # Arrange
    # active_room_fixture ensures the room is occupied
    mocker.patch('utils.support.verify_captcha', return_value=True)
    mock_payment_creator = mocker.patch('schedules.views.Schedules.payment_creator_cls')
    mock_payment_creator.return_value.session.redirect_url = 'http://fakestripesession.com/'
    mocker.patch(
        'schedules.models.Scheduling.full_clean'
    )  # Ensure Scheduling.full_clean does not raise exception
    mocker.patch(
        'reservations.models.Reservation.calc_reservation_value',
        return_value=Decimal('100.00'),
    )  # Mock calc_reservation_value

    url = reverse('schedule', args=[active_room_fixture.pk])

    # Act
    response = client_logged_in.post(url, schedule_form_data)

    # Assert
    # The view redirects to the payment gateway URL
    assert response.status_code == 302
    assert response.url == 'http://fakestripesession.com/'

    sch = Scheduling.objects.last()
    assert sch is not None
    assert (
        sch.reservation.checkin
        == datetime.strptime(schedule_form_data['checkin'], '%Y-%m-%d').date()
    )
    assert (
        sch.reservation.checkout
        == datetime.strptime(schedule_form_data['checkout'], '%Y-%m-%d').date()
    )
    assert sch.reservation.observations == schedule_form_data['obs']
    assert sch.reservation.client == client_fixture


@pytest.mark.django_db
def test_validation_error_renders_schedule_page_with_message(
    mocker, client_logged_in, active_room_fixture, schedule_form_data, get_message
):
    """
    Renders the schedule page again with a message if a validation error occurs.
    """
    # Arrange
    mocker.patch('schedules.views.support.verify_captcha', return_value=True)
    mocker.patch('schedules.views.Schedules.payment_creator_cls')  # Mock this to avoid issues
    mock_payment_full_clean = mocker.patch('schedules.views.Payment.full_clean')
    mock_payment_full_clean.side_effect = ValidationError({'msg': 'error message'})

    url = reverse('schedule', args=[active_room_fixture.pk])

    # Act
    response = client_logged_in.post(url, schedule_form_data)

    # Assert
    assert response.status_code == 200
    assert 'schedule.html' in [t.name for t in response.templates]
    assert get_message(response) == 'error message'


@pytest.mark.django_db
def test_operational_error_redirects_to_rooms_with_message(
    mocker, client_logged_in, active_room_fixture, schedule_form_data, get_message
):
    """
    Tests if an OperationalError redirects to the rooms page with the correct message.
    """
    # Arrange
    mocker.patch('schedules.views.support.verify_captcha', return_value=True)
    mocker.patch('schedules.views.Schedules.payment_creator_cls')  # Mock this to avoid issues
    mock_payment_full_clean = mocker.patch('schedules.views.Payment.full_clean')
    mock_payment_full_clean.side_effect = OperationalError

    url = reverse('schedule', args=[active_room_fixture.pk])

    # Act
    response = client_logged_in.post(url, schedule_form_data)
    messages = [msg.message for msg in get_messages(response.wsgi_request)]

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert messages == [CheckoutMessages.TRANSACTION_BLOCKING]


@pytest.mark.django_db
def test_unexpected_exception_redirects_to_rooms_with_message(
    mocker, client_logged_in, active_room_fixture, schedule_form_data, get_message
):
    """
    Tests if an unexpected exception redirects to the rooms page with the correct message.
    """
    # Arrange
    mocker.patch('schedules.views.support.verify_captcha', return_value=True)
    mocker.patch('schedules.views.Schedules.payment_creator_cls')  # Mock this to avoid issues
    mock_payment_full_clean = mocker.patch('schedules.views.Payment.full_clean')
    mock_payment_full_clean.side_effect = Exception

    url = reverse('schedule', args=[active_room_fixture.pk])

    # Act
    response = client_logged_in.post(url, schedule_form_data)
    messages = [msg.message for msg in get_messages(response.wsgi_request)]

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert messages == [CheckoutMessages.PAYMENT_FAIL]


@pytest.mark.django_db
def test_reservation_validation_failure_renders_schedule_page_with_message(
    mocker, client_logged_in, active_room_fixture, client_fixture, get_message
):
    """
    If reservation validation fails and raises ValidationError, renders the schedule page again with the respective message.
    """
    # Arrange
    mocker.patch('schedules.views.support.verify_captcha', return_value=True)
    mocker.patch('schedules.views.Schedules.payment_creator_cls')  # Mock this to avoid issues

    # Form data that will cause a reservation validation error (e.g., invalid checkin date)
    invalid_schedule_form_data = {
        'checkin': str(date.today() - timedelta(days=1)),  # Invalid checkin date
        'checkout': str(date.today()),
        'obs': '',
    }
    url = reverse('schedule', args=[active_room_fixture.pk])

    # Act
    response = client_logged_in.post(url, invalid_schedule_form_data)

    # Assert
    assert response.status_code == 200
    assert 'schedule.html' in [t.name for t in response.templates]
    assert get_message(response) == ReserveErrorMessages.INVALID_CHECKIN_DATE


@pytest.mark.django_db
def test_invalid_captcha_redirects_to_schedule_with_correct_message(
    mocker, client_logged_in, active_room_fixture, schedule_form_data, get_message
):
    """
    Tests if an invalid captcha redirects back to the schedule page with the correct message.
    """
    # Arrange
    mocker.patch('schedules.views.support.verify_captcha', return_value=False)
    url = reverse('schedule', args=[active_room_fixture.pk])

    # Act
    response = client_logged_in.post(url, schedule_form_data)
    messages = [msg.message for msg in get_messages(response.wsgi_request)]

    # Assert
    assert response.status_code == 302
    assert response.url == url
    assert messages == [INVALID_RECAPTCHA_MESSAGE]


# Tests for ScheduleSuccess View (from TestScheduleSuccess)
@pytest.mark.django_db
def test_payment_sent_in_context(client_logged_in, payment_fixture):
    """
    Test if the payment is sent in the context when rendering HTML.
    """
    # Ensure the reservation and client are refreshed from DB
    payment_fixture.reservation.refresh_from_db()
    payment_fixture.reservation.client.refresh_from_db()

    url = reverse('schedule_success', args=[payment_fixture.reservation.pk])  # Corrected URL
    response = client_logged_in.get(url)
    assert response.status_code == 200
    assert response.context.get('payment') == payment_fixture


@pytest.mark.django_db
def test_payment_saved_correctly(client_logged_in, payment_fixture):
    """
    Test if the payment status is changed to finalized and
    the reservation status to scheduled correctly.
    """
    # Arrange
    payment_fixture.status = 'P'  # Ensure it starts as processing
    payment_fixture.save()
    # Ensure the reservation and client are refreshed from DB
    payment_fixture.reservation.refresh_from_db()
    payment_fixture.reservation.client.refresh_from_db()

    url = reverse('schedule_success', args=[payment_fixture.reservation.pk])  # Corrected URL

    # Act
    client_logged_in.get(url)

    # Assert
    payment_fixture.refresh_from_db()
    assert payment_fixture.status == 'F'
    assert payment_fixture.reservation.status == 'S'


@pytest.mark.django_db
def test_payment_not_processing_renders_page_without_creating_task(
    client_logged_in, payment_fixture
):
    """
    If the payment status is different from processing, it renders the page without
    creating the scheduled task to activate the reservation.
    """
    # Arrange
    payment_fixture.status = 'F'  # Set status to finalized
    payment_fixture.save()
    # Ensure the reservation and client are refreshed from DB
    payment_fixture.reservation.refresh_from_db()
    payment_fixture.reservation.client.refresh_from_db()

    url = reverse('schedule_success', args=[payment_fixture.reservation.pk])  # Corrected URL

    # Construct the expected task name based on the logic in the view
    # This assumes there's only one Scheduling object per Reservation for this payment
    scheduling_obj = payment_fixture.reservation.scheduling_set.first()
    schedule_task_name = f'schedule {scheduling_obj}-{payment_fixture.reservation.client}-{payment_fixture.reservation}'

    # Act
    response = client_logged_in.get(url)

    # Assert
    assert response.status_code == 200
    assert 'schedule_success.html' in [t.name for t in response.templates]
    assert not Schedule.objects.filter(name=schedule_task_name).exists()


@pytest.mark.django_db
def test_creates_schedule_task_correctly(client_logged_in, payment_fixture):
    """
    Test if, upon payment finalization, the scheduling task is created to
    activate the reservation on the scheduled date.
    """
    # Arrange
    payment_fixture.status = 'P'  # Ensure it starts as processing
    payment_fixture.save()
    # Ensure the reservation and client are refreshed from DB
    payment_fixture.reservation.refresh_from_db()
    payment_fixture.reservation.client.refresh_from_db()

    url = reverse('schedule_success', args=[payment_fixture.reservation.pk])  # Corrected URL

    # Act
    client_logged_in.get(url)

    # Assert
    # Construct the expected task name based on the logic in the view
    # This assumes there's only one Scheduling object per Reservation for this payment
    scheduling_obj = payment_fixture.reservation.scheduling_set.first()
    schedule_task_name = f'schedule {scheduling_obj}-{payment_fixture.reservation.client}-{payment_fixture.reservation}'
    assert Schedule.objects.filter(name=schedule_task_name).exists()
