"""
Tests for the payments views.
"""

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from django.contrib.messages import get_messages
from django.db import OperationalError
from django.urls import reverse

from exc import Result
from payments.models import Payment
from payments.error_messages import CheckoutMessages, PaymentCancelMessages

# Checkout view tests


@pytest.fixture
def mock_payment_creator(mocker):
    mock_svc = MagicMock()
    mock_svc.start_checkout.return_value = Result.Ok(
        MagicMock(redirect_url='http://stripepayment-hostedpage.url')
    )
    mocker.patch('payments.views.svc', mock_svc)
    return mock_svc



@pytest.mark.django_db
def test_checkout_view_uses_correct_template(client, client_model, reservation_model):
    """
    Tests if the checkout view renders the correct template.
    """
    # Arrange
    client.force_login(client_model)
    url = reverse('checkout', args=[reservation_model.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    assert 'checkout.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reservation_in_context(client, client_model, reservation_model):
    """
    Tests if the correct reservation is sent in the context.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.context['reservation'] == reservation


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_checkout(client, reservation_model):
    """
    Tests if an unauthenticated user is redirected to the signin page.
    """
    # Arrange
    reservation = reservation_model
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    redirect_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_user_accessing_another_users_checkout_gets_forbidden(client, client_model_factory, reservation_model):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's checkout.
    """
    # Arrange
    user = client_model_factory()
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 403


@pytest.mark.django_db
def test_payment_created_successfully(client, client_model, reservation_model, mock_payment_creator, mock_recaptcha):
    """
    Tests if the payment is created successfully and redirects to the payment page.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = client.post(url, follow=True)

    # Assert
    assert ('http://stripepayment-hostedpage.url', HTTPStatus.FOUND) in response.redirect_chain


@pytest.mark.django_db
def test_operational_error_redirects_to_rooms_with_message(client, client_model, reservation_model, mock_payment_creator, mock_recaptcha):
    """
    Tests if an OperationalError redirects to the rooms page with the correct message.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    mock_payment_creator.start_checkout.return_value = Result.Err('Database error', OperationalError('Database error'))

    # Act
    response = client.post(url)
    messages = list(get_messages(response.wsgi_request))

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert len(messages) > 0
    assert messages[0].message == CheckoutMessages.PAYMENT_FAIL


@pytest.mark.django_db
def test_unexpected_exception_redirects_to_rooms_with_message(client, client_model, reservation_model, mock_payment_creator, mock_recaptcha):
    """
    Tests if an unexpected exception redirects to the rooms page with the correct message.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    mock_payment_creator.start_checkout.return_value = Result.Err('unexpected exception', Exception('unexpected exception'))

    # Act
    response = client.post(url)
    messages = list(get_messages(response.wsgi_request))

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert len(messages) > 0
    assert messages[0].message == CheckoutMessages.PAYMENT_FAIL


@pytest.mark.django_db
def test_payment_is_created_correctly(client, client_model, reservation_model, mock_payment_creator, mock_recaptcha):
    """
    Tests if the payment is created correctly in the database.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])

    # Act
    client.post(url, follow=True)

    # Assert
    mock_payment_creator.start_checkout.assert_called_once_with(
        reservation_id=reservation.pk,
        client_id=user.pk,
        success_url=f'http://testserver/pagamento/success/{reservation.pk}/',
        cancel_url=f'http://testserver/pagamento/cancel/{reservation.pk}/',
    )


# PaymentSuccess view tests


@pytest.mark.django_db
def test_success_view_uses_correct_template(client, payment_model):
    """
    Tests if the success view renders the correct template.
    """
    # Arrange
    user = payment_model.reservation.client
    reservation = payment_model.reservation
    client.force_login(user)
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    assert 'success.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_payment_status_updated_to_finished(client, client_model, reservation_model, payment_model):
    """
    Tests if the payment is updated to finished status after success.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    payment = payment_model
    client.force_login(user)
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    client.get(url)
    payment.refresh_from_db()

    # Assert
    assert payment.status == Payment.Status.COMPLETED


@pytest.mark.django_db
def test_reservation_is_activated(client, client_model, reservation_model, payment_model):
    """
    Tests if the reservation is activated correctly.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    payment = payment_model
    client.force_login(user)
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    client.get(url)
    payment.refresh_from_db()

    # Assert
    assert payment.reservation.status == 'A'


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_success(client, reservation_model):
    """
    Tests if an unauthenticated user is redirected to the signin page.
    """
    # Arrange
    reservation = reservation_model
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    redirect_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_user_accessing_another_users_success_page_gets_forbidden(client, client_model_factory, reservation_model):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's success page.
    """
    # Arrange
    user = client_model_factory()
    reservation = reservation_model
    client.force_login(user)
    url = reverse('payment_success', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 403


# PaymentCancel view tests


@pytest.mark.django_db
def test_cancel_view_uses_correct_template(client, payment_model):
    """
    Tests if the cancel view renders the correct template.
    """
    # Arrange
    user = payment_model.reservation.client
    reservation = payment_model.reservation
    client.force_login(user)
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    assert 'cancel.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_payment_and_reservation_status_change_to_cancelled(client, payment_model):
    """
    Tests if the payment and reservation status are changed to cancelled and the room is released.
    """
    # Arrange
    user = payment_model.reservation.client
    reservation = payment_model.reservation
    payment = payment_model
    client.force_login(user)
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    client.get(url)
    payment.refresh_from_db()
    payment.reservation.room.refresh_from_db()

    # Assert
    assert payment.status == Payment.Status.FAILED
    assert payment.reservation.status == 'C'
    assert payment.reservation.room.available


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_cancel(client, reservation_model):
    """
    Tests if an unauthenticated user is redirected to the signin page.
    """
    # Arrange
    reservation = reservation_model
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    redirect_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_user_accessing_another_users_cancel_page_gets_forbidden(client, client_model_factory, reservation_model):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's cancel page.
    """
    # Arrange
    user = client_model_factory()
    reservation = reservation_model
    client.force_login(user)
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 403


@pytest.mark.django_db
def test_unexpected_exception_in_cancel_view_redirects_with_message(
    client, client_model, reservation_model, mocker
):
    """
    Tests if an unexpected exception redirects to the rooms page with the correct message.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
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
