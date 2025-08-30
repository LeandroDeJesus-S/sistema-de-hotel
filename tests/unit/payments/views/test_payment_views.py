"""
Tests for the payments views.
"""

from http import HTTPStatus

import pytest
from django.contrib.messages import get_messages
from django.db import OperationalError
from django.urls import reverse

from payments.models import Payment
from utils.supportviews import CheckoutMessages, PaymentCancelMessages

# Checkout view tests


@pytest.mark.django_db
def test_checkout_view_uses_correct_template(client, view_setup):
    """
    Tests if the checkout view renders the correct template.
    """
    # Arrange
    user, _, reservation, _ = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    assert 'checkout.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reservation_in_context(client, view_setup):
    """
    Tests if the correct reservation is sent in the context.
    """
    # Arrange
    user, _, reservation, _ = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.context['reservation'] == reservation


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_checkout(client, view_setup):
    """
    Tests if an unauthenticated user is redirected to the signin page.
    """
    # Arrange
    _, _, reservation, _ = view_setup
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    redirect_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_user_accessing_another_users_checkout_gets_forbidden(client, view_setup):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's checkout.
    """
    # Arrange
    user, _, _, reservation2 = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation2.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 403


@pytest.mark.django_db
def test_payment_created_successfully(client, view_setup, mocker):
    """
    Tests if the payment is created successfully and redirects to the payment page.
    """
    # Arrange
    user, _, reservation, _ = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    mocker.patch('utils.support.verify_captcha', return_value=True)
    mock_creator = mocker.patch('payments.views.Checkout.payment_creator_cls')
    mock_creator.return_value.session.redirect_url = 'http://stripepayment-hostedpage.url'

    # Act
    response = client.post(url, follow=True)

    # Assert
    assert ('http://stripepayment-hostedpage.url', HTTPStatus.FOUND) in response.redirect_chain


@pytest.mark.django_db
def test_operational_error_redirects_to_rooms_with_message(client, view_setup, mocker):
    """
    Tests if an OperationalError redirects to the rooms page with the correct message.
    """
    # Arrange
    user, _, reservation, _ = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    mocker.patch('utils.support.verify_captcha', return_value=True)
    mocker.patch('payments.views.Checkout.payment_creator_cls')
    mocker.patch('payments.views.Payment.save', side_effect=OperationalError('Database error'))

    # Act
    response = client.post(url)
    messages = list(get_messages(response.wsgi_request))

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert len(messages) > 0
    assert messages[0].message == CheckoutMessages.TRANSACTION_BLOCKING


@pytest.mark.django_db
def test_unexpected_exception_redirects_to_rooms_with_message(client, view_setup, mocker):
    """
    Tests if an unexpected exception redirects to the rooms page with the correct message.
    """
    # Arrange
    user, _, reservation, _ = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    mocker.patch('utils.support.verify_captcha', return_value=True)
    mocker.patch('payments.views.Checkout.payment_creator_cls')
    mocker.patch('payments.views.Payment.save', side_effect=Exception('unexpected exception'))

    # Act
    response = client.post(url)
    messages = list(get_messages(response.wsgi_request))

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert len(messages) > 0
    assert messages[0].message == CheckoutMessages.PAYMENT_FAIL


@pytest.mark.django_db
def test_reservation_status_changes_and_room_becomes_unavailable(client, view_setup, mocker):
    """
    Tests if the reservation status changes to processing and the room becomes unavailable.
    """
    # Arrange
    user, _, reservation, _ = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    mocker.patch('utils.support.verify_captcha', return_value=True)
    mocker.patch('payments.views.Checkout.payment_creator_cls')

    # Act
    client.post(url, follow=True)
    reservation.refresh_from_db()
    reservation.room.refresh_from_db()

    # Assert
    assert reservation.status == 'P'
    assert not reservation.room.available


@pytest.mark.django_db
def test_payment_is_created_correctly(client, view_setup, mocker):
    """
    Tests if the payment is created correctly in the database.
    """
    # Arrange
    user, _, reservation, _ = view_setup
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    mocker.patch('utils.support.verify_captcha', return_value=True)
    mocker.patch('payments.views.Checkout.payment_creator_cls')

    # Act
    client.post(url, follow=True)
    payment = Payment.objects.last()

    # Assert
    assert payment is not None
    assert payment.reservation == reservation
    assert payment.status == 'P'


# PaymentSuccess view tests


@pytest.mark.django_db
def test_success_view_uses_correct_template(client, success_view_setup):
    """
    Tests if the success view renders the correct template.
    """
    # Arrange
    user, _, reservation, _, _ = success_view_setup
    client.force_login(user)
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    assert 'success.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_payment_status_updated_to_finished(client, success_view_setup):
    """
    Tests if the payment is updated to finished status after success.
    """
    # Arrange
    user, _, reservation, _, payment = success_view_setup
    client.force_login(user)
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    client.get(url)
    payment.refresh_from_db()

    # Assert
    assert payment.status == 'F'


@pytest.mark.django_db
def test_reservation_is_activated(client, success_view_setup):
    """
    Tests if the reservation is activated correctly.
    """
    # Arrange
    user, _, reservation, _, payment = success_view_setup
    client.force_login(user)
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    client.get(url)
    payment.refresh_from_db()

    # Assert
    assert payment.reservation.status == 'A'
    assert payment.reservation.active


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_success(client, success_view_setup):
    """
    Tests if an unauthenticated user is redirected to the signin page.
    """
    # Arrange
    _, _, reservation, _, _ = success_view_setup
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    redirect_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_user_accessing_another_users_success_page_gets_forbidden(client, success_view_setup):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's success page.
    """
    # Arrange
    user, _, _, reservation2, _ = success_view_setup
    client.force_login(user)
    url = reverse('payment_success', args=[reservation2.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 403


# PaymentCancel view tests


@pytest.mark.django_db
def test_cancel_view_uses_correct_template(client, cancel_view_setup):
    """
    Tests if the cancel view renders the correct template.
    """
    # Arrange
    user, _, reservation, _, _ = cancel_view_setup
    client.force_login(user)
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    assert 'cancel.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_payment_and_reservation_status_change_to_cancelled(client, cancel_view_setup):
    """
    Tests if the payment and reservation status are changed to cancelled and the room is released.
    """
    # Arrange
    user, _, reservation, _, payment = cancel_view_setup
    client.force_login(user)
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    client.get(url)
    payment.refresh_from_db()
    payment.reservation.room.refresh_from_db()

    # Assert
    assert payment.status == 'C'
    assert payment.reservation.status == 'C'
    assert payment.reservation.room.available


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_cancel(client, cancel_view_setup):
    """
    Tests if an unauthenticated user is redirected to the signin page.
    """
    # Arrange
    _, _, reservation, _, _ = cancel_view_setup
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    redirect_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_user_accessing_another_users_cancel_page_gets_forbidden(client, cancel_view_setup):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's cancel page.
    """
    # Arrange
    user, _, _, reservation2, _ = cancel_view_setup
    client.force_login(user)
    url = reverse('payment_cancel', args=[reservation2.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 403


@pytest.mark.django_db
def test_unexpected_exception_in_cancel_view_redirects_with_message(
    client, cancel_view_setup, mocker
):
    """
    Tests if an unexpected exception redirects to the rooms page with the correct message.
    """
    # Arrange
    user, _, reservation, _, _ = cancel_view_setup
    client.force_login(user)
    url = reverse('payment_cancel', args=[reservation.pk])
    mocker.patch('payments.views.get_object_or_404', side_effect=Exception)

    # Act
    response = client.get(url)
    messages = list(get_messages(response.wsgi_request))

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert len(messages) > 0
    assert messages[0].message == PaymentCancelMessages.UNEXPECTED_ERROR
