import pytest
from django.urls import reverse
from http import HTTPStatus
from ddf import G

from clients.models import Client


@pytest.mark.django_db
def test_perfil_template_is_rendered(authenticated_client, perfil_urls):
    """
    Test if it renders the perfil.html template.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_url']

    # Act
    response = client.get(url)

    # Assert
    assert 'perfil.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_correct_client_data_is_shown(authenticated_client, perfil_urls, user):
    """
    Test if the profile being shown is the correct client's profile.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_url']
    context_obj_name = perfil_urls['perfil_context_obj_name']

    # Act
    response = client.get(url)
    perfil = response.context[context_obj_name]

    # Assert
    assert perfil == user


@pytest.mark.django_db
def test_unauthenticated_client_is_redirected(client, perfil_urls):
    """
    Test if an unauthenticated client trying to access the profile is redirected.
    """
    # Arrange
    url = perfil_urls['perfil_url']

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND


@pytest.mark.django_db
def test_unauthenticated_client_is_redirected_to_signin(client, perfil_urls):
    """
    Test if an unauthenticated client is redirected to the signin page.
    """
    # Arrange
    url = perfil_urls['perfil_url']
    signin_url = reverse('signin')
    next_url_field_name = perfil_urls['next_url_field_name']
    expected_url = f'{signin_url}?{next_url_field_name}={url}'

    # Act
    response = client.get(url)

    # Assert
    assert response.url == expected_url


@pytest.mark.django_db
def test_client_accessing_another_perfil_receives_http_forbidden(authenticated_client):
    """
    Test if a client trying to access a profile that is not theirs receives an HTTP 403 Forbidden error.
    """
    # Arrange
    client, _ = authenticated_client
    other_user = G(Client)
    url = reverse('perfil', args=[other_user.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == HTTPStatus.FORBIDDEN