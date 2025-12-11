from http import HTTPStatus

import pytest
from ddf import G
from django.urls import reverse

from clients.models import Client


@pytest.mark.django_db
def test_perfil_delete_template_is_rendered(authenticated_client, perfil_urls):
    """
    Test if it renders the correct template.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_delete_url']

    # Act
    response = client.get(url)

    # Assert
    assert 'perfil_delete.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_unauthenticated_client_is_redirected(client, perfil_urls):
    """
    Test if an unauthenticated client is redirected when trying to access the delete profile page.
    """
    # Arrange
    url = perfil_urls['perfil_delete_url']

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
    url = perfil_urls['perfil_delete_url']
    signin_url = reverse('signin')
    next_url_field_name = perfil_urls['next_url_field_name']
    expected_url = f'{signin_url}?{next_url_field_name}={url}'

    # Act
    response = client.get(url)

    # Assert
    assert response.url == expected_url


@pytest.mark.django_db
def test_authenticated_client_cannot_access_another_perfil_delete_receives_403(
    authenticated_client,
):
    """
    Test if a logged-in client is not able to access another client's profile delete page, receiving HTTP Forbidden.
    """
    # Arrange
    client, _ = authenticated_client
    other_user = G(Client)
    url = reverse('delete_perfil', args=[other_user.pk])

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_authenticated_client_cannot_delete_another_perfil_receives_403(authenticated_client):
    """
    Test if a logged-in client is not able to delete another client's profile, receiving HTTP Forbidden.
    """
    # Arrange
    client, _ = authenticated_client
    other_user = G(Client)
    url = reverse('delete_perfil', args=[other_user.pk])

    # Act
    response = client.post(url)

    # Assert
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_success_url_after_delete_is_redirect(
    authenticated_client, perfil_urls, mock_recaptcha
):
    """
    Test if it redirects after deleting the profile.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_delete_url']

    # Act
    response = client.post(url)

    # Assert
    assert response.status_code == HTTPStatus.FOUND


@pytest.mark.django_db
def test_success_url_after_delete_is_correct(
    authenticated_client, perfil_urls, mock_recaptcha
):
    """
    Test if it redirects to the correct URL after deleting the profile.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_delete_url']
    success_url = perfil_urls['perfil_delete_success_url']

    # Act
    response = client.post(url)

    # Assert
    assert response.url == success_url


@pytest.mark.django_db
def test_client_is_deleted_if_all_goes_as_expected(
    authenticated_client, perfil_urls, client_model, mock_recaptcha
):
    """
    Test the deletion of a client if everything goes as expected.
    """
    # Arrange
    client, _ = authenticated_client
    url = perfil_urls['perfil_delete_url']

    # Act
    client.post(url)

    # Assert
    with pytest.raises(Client.DoesNotExist):
        Client.objects.get(pk=client_model.pk)
