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
from payments.application.services import PaymentService
from payments.error_messages import CheckoutMessages
# Checkout view tests


@pytest.mark.django_db
def test_checkout_view_uses_correct_template(client, client_model, reservation_model, mocker):
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
    assert response.context['reservation'].id == reservation.id


@pytest.mark.django_db
def test_unauthenticated_user_is_redirected_from_checkout(client, reservation_model, mocker):
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
def test_user_accessing_another_users_checkout_gets_forbidden(
    client_model_factory, reservation_model_factory, authenticated_client
):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's checkout.
    """
    # Arrange
    http_client, _ = authenticated_client
    another_user = client_model_factory()
    reservation = reservation_model_factory(client=another_user)
    url = reverse('checkout', args=[reservation.pk])

    # Act
    response = http_client.get(url)

    # Assert
    assert response.status_code == 403


@pytest.mark.django_db
def test_payment_created_successfully(
    client, client_model, reservation_model, mock_recaptcha, mocker, payments_container
):
    """
    Tests if the payment is created successfully and redirects to the payment page.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    svc_mock = mocker.MagicMock(spec=PaymentService)
    svc_mock.handle_checkout.return_value = Result.Ok(
        MagicMock(session_url='http://stripepayment-hostedpage.url')
    )

    # Act
    with payments_container.payment_service.override(svc_mock):
        response = client.post(url, follow=True)

    # Assert
    assert ('http://stripepayment-hostedpage.url', HTTPStatus.FOUND) in response.redirect_chain


@pytest.mark.django_db
def test_operational_error_redirects_to_rooms_with_message(
    client, client_model, reservation_model, mock_recaptcha, mocker, payments_container
):
    """
    Tests if an OperationalError redirects to the rooms page with the correct message.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    svc_mock = mocker.MagicMock(spec=PaymentService)
    svc_mock.handle_checkout.return_value = Result.Err(
        'Database error', OperationalError('Database error')
    )

    # Act
    with payments_container.payment_service.override(svc_mock):
        response = client.post(url)
    messages = list(get_messages(response.wsgi_request))

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert len(messages) > 0
    assert messages[0].message == CheckoutMessages.PAYMENT_FAIL


@pytest.mark.django_db
def test_unexpected_exception_redirects_to_rooms_with_message(
    client, client_model, reservation_model, mock_recaptcha, mocker, payments_container
):
    """
    Tests if an unexpected exception redirects to the rooms page with the correct message.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    svc_mock = mocker.MagicMock(spec=PaymentService)
    svc_mock.handle_checkout.return_value = Result.Err(
        'unexpected exception', Exception('unexpected exception')
    )

    # Act
    with payments_container.payment_service.override(svc_mock):
        response = client.post(url)
    messages = list(get_messages(response.wsgi_request))

    # Assert
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert len(messages) > 0
    assert messages[0].message == CheckoutMessages.PAYMENT_FAIL


@pytest.mark.django_db
def test_payment_is_created_correctly(
    client, client_model, reservation_model, mock_recaptcha, mocker, payments_container
):
    """
    Tests if the payment is created correctly in the database.
    """
    # Arrange
    user = client_model
    reservation = reservation_model
    client.force_login(user)
    url = reverse('checkout', args=[reservation.pk])
    svc_mock = mocker.MagicMock(spec=PaymentService)
    svc_mock.handle_checkout.return_value = Result.Ok(
        MagicMock(session_url='http://stripepayment-hostedpage.url')
    )

    # Act
    with payments_container.payment_service.override(svc_mock):
        client.post(url, follow=True)

    # Assert
    svc_mock.handle_checkout.assert_called_once_with(
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
def test_unauthenticated_user_is_redirected_from_success(client, reservation_model, mocker):
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
def test_user_accessing_another_users_success_page_gets_forbidden(
    client_model_factory, reservation_model_factory, authenticated_client
):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's success page.
    """
    # Arrange
    http_client, _ = authenticated_client
    another_user = client_model_factory()
    reservation = reservation_model_factory(client=another_user)

    url = reverse('payment_success', args=[reservation.pk])

    # Act
    response = http_client.get(url)

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
def test_unauthenticated_user_is_redirected_from_cancel(client, reservation_model, mocker):
    """
    Tests if an unauthenticated user is redirected to the signin page.
    """
    # Arrange
    mocker.patch('reservations.decorators.check_reservation_ownership', new=lambda x: x)
    reservation = reservation_model
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    response = client.get(url)

    # Assert
    redirect_url = reverse('signin') + f'?next={url}'
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_user_accessing_another_users_cancel_page_gets_forbidden(
    authenticated_client, client_model_factory, reservation_model_factory
):
    """
    Tests if a user gets a 403 Forbidden error when trying to access another user's cancel page.
    """
    # Arrange
    http_client, _ = authenticated_client
    another_user = client_model_factory()
    reservation = reservation_model_factory(client=another_user)
    url = reverse('payment_cancel', args=[reservation.pk])

    # Act
    response = http_client.get(url)

    # Assert
    assert response.status_code == 403
