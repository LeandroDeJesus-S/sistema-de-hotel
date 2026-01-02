from http import HTTPStatus

import pytest
from ddf import G
from django.urls import reverse

from clients.models import Client


@pytest.mark.django_db
def test_perfil_update_template_is_rendered(authenticated_client, perfil_urls):
    """
    Test if it renders the perfil_update.html template as expected.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_update_url']

    # Act
    response = client.get(url)

    # Assert
    assert 'perfil_update.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_unauthenticated_client_is_redirected(client, perfil_urls):
    """
    Test if an unauthenticated user is redirected if they try to update their profile without being logged in.
    """
    # Arrange
    url = perfil_urls['perfil_update_url']

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND


@pytest.mark.django_db
def test_unauthenticated_client_is_redirected_to_signin(client, perfil_urls):
    """
    Test if an unauthenticated user is redirected to signin if they try to update their profile without being logged in.
    """
    # Arrange
    url = perfil_urls['perfil_update_url']
    signin_url = reverse('signin')
    next_url_field_name = perfil_urls['next_url_field_name']
    expected_url = f'{signin_url}?{next_url_field_name}={url}'

    # Act
    response = client.get(url)

    # Assert
    assert response.url == expected_url


@pytest.mark.django_db
def test_authenticated_client_accessing_another_perfil_update_receives_http_forbidden(
    authenticated_client,
):
    """
    Test if a logged-in client trying to access another client's data update page receives HTTP Forbidden.
    """
    # Arrange
    client, _ = authenticated_client
    other_user = G(Client)
    url = reverse('update_perfil', args=[other_user.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_authenticated_client_updating_another_perfil_receives_http_forbidden(
    authenticated_client, client_model
):
    """
    Test if a logged-in client trying to update another client's data receives HTTP Forbidden.
    """
    # Arrange
    client, _ = authenticated_client
    other_user = G(Client)
    url = reverse('update_perfil', args=[other_user.pk])
    data = {
        'username': 'new username',
        'first_name': client_model.first_name,
        'last_name': client_model.last_name,
        'phone': client_model.phone,
        'email': client_model.email,
        'birthdate': client_model.birthdate,
        'cpf': client_model.cpf,
    }

    # Act
    response = client.post(url, data=data)

    # Assert
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_client_updates_email_correctly(
    authenticated_client, perfil_urls, client_model, mock_recaptcha
):
    """
    Test if a logged-in client can update their email correctly as expected.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_update_url']
    new_email = 'updated@email.com'
    data = {
        'username': client_model.username,
        'first_name': client_model.first_name,
        'last_name': client_model.last_name,
        'phone': client_model.phone,
        'email': new_email,
        'birthdate': client_model.birthdate,
        'cpf': client_model.cpf,
    }

    # Act
    client.post(url, data=data)
    updated_user = Client.objects.get(pk=client_model.pk)

    # Assert
    assert updated_user.email == new_email


@pytest.mark.django_db
def test_client_updates_username_correctly(
    authenticated_client, perfil_urls, client_model, mock_recaptcha
):
    """
    Test if a logged-in client can update their username correctly as expected.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_update_url']
    new_username = 'updatedusername'
    data = {
        'username': new_username,
        'first_name': client_model.first_name,
        'last_name': client_model.last_name,
        'phone': client_model.phone,
        'email': client_model.email,
        'birthdate': client_model.birthdate,
        'cpf': client_model.cpf,
    }

    # Act
    client.post(url, data=data)
    updated_user = Client.objects.get(pk=client_model.pk)

    # Assert
    assert updated_user.username == new_username
