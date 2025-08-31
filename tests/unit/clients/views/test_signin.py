from http import HTTPStatus

import pytest
from django.core.management import call_command
from django.test import Client as DjClient
from django.urls import reverse

from reservations.models import Room
from utils.supporttest import get_message
from clients.error_messages import SignInMessages


@pytest.fixture(scope='function')
def room(db):
    """
    Loads necessary fixtures and returns a Room object.
    """
    call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
    call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
    call_command('loaddata', 'tests/fixtures/classe_fixture.json')
    call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
    return Room.objects.get(pk=1)


@pytest.fixture(scope='function')
def reserve_url(room):
    """
    Provides the URL for reserving a room.
    """
    return reverse('reserve', args=(room.pk,))


@pytest.fixture(scope='function')
def signin_data(user):
    """
    Provides valid signin data.
    """
    return {'username': user.username, 'password': user.password}


@pytest.fixture(scope='function')
def signin_user(user):
    """
    Sets the user's password and saves it.
    """
    plain_password = 'test_password_123'
    user.set_password(plain_password)
    user.save()
    user.plain_password = plain_password
    return user


@pytest.mark.django_db
def test_signin_template(client, signin_urls):
    """
    Test if signin renders the correct template.
    """
    # Arrange
    url = signin_urls['signin_url']

    # Act
    response = client.get(url)

    # Assert
    assert 'signin.html' in [t.name for t in response.templates]


def test_authenticated_client_redirected_to_rooms(authenticated_client, signin_urls):
    """
    Test if an already logged-in client is redirected to the rooms page when trying to access signin.
    """
    # Arrange
    client, _ = authenticated_client
    url = signin_urls['signin_url']
    rooms_url = signin_urls['rooms_url']

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == rooms_url


@pytest.mark.django_db
def test_client_logged_in_with_valid_username_and_password(
    mocker, client, signin_urls, signin_user
):
    """
    Test if the user is logged in correctly via valid username and password.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    url = signin_urls['signin_url']
    data = {'username': signin_user.username, 'password': signin_user.plain_password}

    # Act
    response = client.post(url, data)

    # Assert
    assert response.wsgi_request.user.is_authenticated, response.content.decode()


@pytest.mark.django_db
def test_client_logged_in_with_valid_email_and_password(
    mocker, client, signin_urls, signin_user
):
    """
    Test if the user is logged in correctly using valid email and password.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    url = signin_urls['signin_url']
    data = {'username': signin_user.email, 'password': signin_user.plain_password}

    # Act
    response = client.post(url, data)

    # Assert
    assert response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_client_redirected_to_rooms_after_login(mocker, client, signin_urls, signin_user):
    """
    Test if after logging in, the client is redirected to the rooms page.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    url = signin_urls['signin_url']
    rooms_url = signin_urls['rooms_url']
    data = {'username': signin_user.username, 'password': signin_user.plain_password}

    # Act
    response = client.post(url, data)

    # Assert
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == rooms_url


@pytest.mark.parametrize(
    ('username', 'password', 'expected_message'),
    [
        ('invalid_username', 'test_password_123', SignInMessages.INVALID_CREDENTIALS),
        ('test_username', 'invalid_password', SignInMessages.INVALID_CREDENTIALS),
        ('email@email.com', 'invalid_password', SignInMessages.INVALID_CREDENTIALS),
    ],
)
@pytest.mark.django_db
def test_invalid_credentials_render_signin_with_message(
    mocker,
    client,
    signin_urls,
    signin_user,
    username,
    password,
    expected_message,
):
    """
    Test if invalid credentials render the signin page again with the correct message.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    url = signin_urls['signin_url']
    data = {'username': username, 'password': password}

    # Act
    response = client.post(url, data)
    message = get_message(response)

    # Assert
    assert message == expected_message


@pytest.mark.parametrize(
    ('username', 'password'),
    [
        ('invalid_username', 'test_password_123'),
        ('test_username', 'invalid_password'),
        ('email@email.com', 'invalid_password'),
    ],
)
@pytest.mark.django_db
def test_invalid_credentials_render_correct_template(
    mocker,
    client,
    signin_urls,
    signin_user,
    username,
    password,
):
    """
    Test if invalid credentials render the signin page again with the correct template.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    url = signin_urls['signin_url']
    data = {'username': username, 'password': password}

    # Act
    response = client.post(url, data)

    # Assert
    assert 'signin.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_unauthenticated_client_redirected_to_signin_with_next_url_field_when_reserving(
    client,
    signin_urls,
    reserve_url,
):
    """
    Test if an unauthenticated client trying to reserve is redirected to signin
    with a next URL argument for redirection.
    """
    # Arrange
    next_url_field_name = signin_urls['next_url_field_name']
    signin_url = signin_urls['signin_url']
    expected_url = f'{signin_url}?{next_url_field_name}={reserve_url}'

    # Act
    response = client.get(reserve_url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == expected_url


@pytest.mark.django_db
def test_client_redirected_to_reserve_after_login_from_next_url(
    mocker,
    client: DjClient,
    signin_urls,
    signin_user,
    reserve_url,
):
    """
    Test if after trying to reserve without being logged in, being redirected to signin,
    and completing the login, the client is redirected to the reserve page.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    signin_url = signin_urls['signin_url']
    next_url = reserve_url
    response = client.get(signin_url, {'next': next_url})

    data = {'username': signin_user.username, 'password': signin_user.plain_password}

    # Act
    response = response.client.post(signin_url, data)

    # Assert
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reserve_url


@pytest.mark.parametrize(
    ('username', 'password', 'expected_message'),
    [
        ('', 'test_password_123', SignInMessages.INVALID_CREDENTIALS),
        ('test_username', '', SignInMessages.INVALID_CREDENTIALS),
        ('email@email.com', '', SignInMessages.INVALID_CREDENTIALS),
    ],
)
@pytest.mark.django_db
def test_missing_credentials_render_signin_with_message(
    mocker,
    client,
    signin_urls,
    signin_user,
    username,
    password,
    expected_message,
):
    """
    Test if not providing all necessary credentials renders the signin page again with a message.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    url = signin_urls['signin_url']
    data = {'username': username, 'password': password}

    # Act
    response = client.post(url, data)
    message = get_message(response)

    # Assert
    assert message == expected_message


@pytest.mark.parametrize(
    ('username', 'password'),
    [
        ('', 'test_password_123'),
        ('test_username', ''),
        ('email@email.com', ''),
    ],
)
@pytest.mark.django_db
def test_missing_credentials_render_correct_template(
    mocker,
    client,
    signin_urls,
    signin_user,
    username,
    password,
):
    """
    Test if not providing all necessary credentials renders the signin page again with the correct template.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    url = signin_urls['signin_url']
    data = {'username': username, 'password': password}

    # Act
    response = client.post(url, data)

    # Assert
    assert 'signin.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_next_url_deleted_from_session_after_post_capture(
    mocker,
    client,
    signin_urls,
    signin_user,
    reserve_url,
):
    """
    Test if after capturing next_url via session in the POST method, it is removed from the session.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=True)
    signin_url = signin_urls['signin_url']
    data = {'username': signin_user.username, 'password': signin_user.plain_password}

    # Act
    client.get(reserve_url)  # This sets the 'next' URL in the session
    response = client.post(signin_url, data)

    # Assert
    assert 'next_url' not in client.session


@pytest.mark.django_db
def test_signin_invalid_captcha_redirects_to_signin_with_message(
    mocker,
    client,
    signin_urls,
    signin_user,
):
    """
    Test if an invalid captcha redirects back to the login page with the correct message.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=False)
    url = signin_urls['signin_url']
    data = {'username': signin_user.username, 'password': signin_user.plain_password}

    # Act
    response = client.post(url, data)
    message = get_message(response)

    # Assert
    assert message == 'Mr. Robot, é você???'


@pytest.mark.django_db
def test_signin_invalid_captcha_redirects_to_signin(
    mocker,
    client,
    signin_urls,
    signin_user,
):
    """
    Test if an invalid captcha redirects back to the login page.
    """
    # Arrange
    mocker.patch('clients.views.support.verify_captcha', return_value=False)
    url = signin_urls['signin_url']
    data = {'username': signin_user.username, 'password': signin_user.plain_password}

    # Act
    response = client.post(url, data)

    # Assert
    assert response.url == url
