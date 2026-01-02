from http import HTTPStatus

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_logged_in_user_is_logged_out(authenticated_client):
    """
    Test if a logged-in user is logged out as expected.
    """
    # Arrange
    client, _ = authenticated_client
    logout_url = reverse('logout')

    # Act
    response = client.get(logout_url)

    # Assert
    assert not response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_logged_out_user_redirected_to_signin(authenticated_client):
    """
    Test if after logging out, the user is redirected to signin.
    """
    # Arrange
    client, _ = authenticated_client
    logout_url = reverse('logout')
    signin_url = reverse('signin')

    # Act
    response = client.get(logout_url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == signin_url


@pytest.mark.django_db
def test_never_logged_in_user_redirected_to_signin(client):
    """
    Test if a user who has never been logged in and tries to access
    logout is redirected to signin.
    """
    # Arrange
    logout_url = reverse('logout')
    signin_url = reverse('signin')

    # Act
    response = client.get(logout_url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == signin_url
