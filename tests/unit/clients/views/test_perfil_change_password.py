from http import HTTPStatus

import pytest
from ddf import G
from django.urls import reverse

from clients.models import Client
from utils.supporttest import get_message
from clients.error_messages import PerfilChangePasswordMessages


@pytest.fixture(scope='function')
def change_password_data():
    """
    Provides data for changing password.
    """
    return {'new_password': 'novasenha@01', 'password_repeat': 'novasenha@01'}


@pytest.mark.django_db
def test_perfil_change_password_template_is_rendered(authenticated_client, perfil_urls):
    """
    Test if it renders the perfil_update_password.html template.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_change_pw_url']

    # Act
    response = client.get(url)

    # Assert
    assert 'perfil_update_password.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_unauthenticated_client_is_redirected(client, perfil_urls):
    """
    Test if an unauthenticated client is prompted to log in before accessing the password update page.
    """
    # Arrange
    url = perfil_urls['perfil_change_pw_url']

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND


@pytest.mark.django_db
def test_unauthenticated_client_is_redirected_to_signin(client, perfil_urls):
    """
    Test if an unauthenticated client is prompted to log in before accessing the password update page.
    """
    # Arrange
    url = perfil_urls['perfil_change_pw_url']
    signin_url = reverse('signin')
    next_url_field_name = perfil_urls['next_url_field_name']
    expected_url = f'{signin_url}?{next_url_field_name}={url}'

    # Act
    response = client.get(url)

    # Assert
    assert response.url == expected_url


@pytest.mark.django_db
def test_authenticated_client_cannot_change_another_client_password_forbidden(
    mocker, authenticated_client, change_password_data
):
    """
    Test if a logged-in client trying to change another client's password receives HTTP Forbidden.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    client, _ = authenticated_client
    other_user = G(Client)
    url = reverse('update_perfil_password', args=[other_user.pk])

    # Act
    response = client.post(url, change_password_data)

    # Assert
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_authenticated_client_cannot_change_another_client_password_not_persisted(
    mocker, authenticated_client, change_password_data
):
    """
    Test if a logged-in client trying to change another client's password is not persisted.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    client, _ = authenticated_client
    other_user = G(Client)
    url = reverse('update_perfil_password', args=[other_user.pk])

    # Act
    client.post(url, change_password_data)
    other_user.refresh_from_db()

    # Assert
    assert not other_user.check_password(change_password_data['new_password'])


@pytest.mark.django_db
def test_different_passwords_do_not_pass_validation_and_redirects(
    mocker, authenticated_client, perfil_urls, change_password_data
):
    """
    If the client does not send identical passwords, validation does not proceed
    and redirects.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    client, _ = authenticated_client
    url = perfil_urls['perfil_change_pw_url']
    data = change_password_data.copy()
    data['password_repeat'] = data['password_repeat'].title()  # Make passwords different

    # Act
    response = client.post(url, data)

    # Assert
    assert response.status_code == HTTPStatus.FOUND


@pytest.mark.django_db
def test_different_passwords_do_not_pass_validation_and_redirects_to_perfil(
    mocker, authenticated_client, perfil_urls, change_password_data
):
    """
    If the client does not send identical passwords, validation does not proceed
    and redirects to the profile page.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    client, _ = authenticated_client
    url = perfil_urls['perfil_change_pw_url']
    data = change_password_data.copy()
    data['password_repeat'] = data['password_repeat'].title()  # Make passwords different

    # Act
    response = client.post(url, data)

    # Assert
    assert response.url == perfil_urls['perfil_url']


@pytest.mark.django_db
def test_message_when_passwords_differ(
    mocker, authenticated_client, perfil_urls, change_password_data
):
    """
    Test if the message for different passwords is correct.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    client, _ = authenticated_client
    url = perfil_urls['perfil_change_pw_url']
    data = change_password_data.copy()
    data['password_repeat'] = data['password_repeat'].title()  # Make passwords different

    # Act
    response = client.post(url, data)
    message = get_message(response)

    # Assert
    assert message == PerfilChangePasswordMessages.PASSWORDS_DIFFER


@pytest.mark.django_db
def test_message_when_password_changed_successfully(
    mocker, authenticated_client, perfil_urls, change_password_data
):
    """
    Test if the password changed successfully message is correct.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    client, user = authenticated_client
    client.force_login(user)
    url = perfil_urls['perfil_change_pw_url']

    # Act
    response = client.post(url, change_password_data)
    message = get_message(response)

    # Assert
    assert message == PerfilChangePasswordMessages.SUCCESS


@pytest.mark.django_db
def test_password_persisted_correctly_in_database(
    mocker, authenticated_client, perfil_urls, change_password_data, user
):
    """
    Test if the password is validly persisted in the database.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    client, auth_user = authenticated_client
    client.force_login(auth_user)
    url = perfil_urls['perfil_change_pw_url']

    # Act
    client.post(url, change_password_data)
    user.refresh_from_db()

    # Assert
    assert user.check_password(change_password_data['new_password'])


@pytest.mark.django_db
def test_invalid_captcha_redirects_with_message(
    mocker, authenticated_client, perfil_urls, change_password_data
):
    """
    Test if an invalid captcha redirects back with the correct message.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=False)
    client, _ = authenticated_client
    url = perfil_urls['perfil_change_pw_url']

    # Act
    response = client.post(url, change_password_data)
    message = get_message(response)

    # Assert
    assert message == 'Mr. Robot, é você???'


@pytest.mark.django_db
def test_invalid_captcha_redirects_to_perfil_change_password_page(
    mocker, authenticated_client, perfil_urls, change_password_data
):
    """
    Test if an invalid captcha redirects back to the update password page.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=False)
    client, _ = authenticated_client
    url = perfil_urls['perfil_change_pw_url']

    # Act
    response = client.post(url, change_password_data)

    # Assert
    assert response.url == url
