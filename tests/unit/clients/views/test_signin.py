import pytest
import responses
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date


@pytest.mark.django_db
def test_signin_success(client, client_model, mock_recaptcha):
    """Test that a user can sign in successfully."""
    signin_url = reverse('signin')
    post_data = {
        'username': client_model.username,
        'password': client_model.raw_password,
        'g-recaptcha-response': 'fake-token',
    }

    response = client.post(signin_url, post_data)

    assert response.wsgi_request.user.is_authenticated, 'user not authenticated'


@pytest.mark.django_db
def test_signin_invalid_credentials(client, client_model, responses, settings):
    """Test that sign in fails with invalid credentials."""
    # Disable django-axes middleware for this test
    settings.MIDDLEWARE = [
        m for m in settings.MIDDLEWARE if m != 'axes.middleware.AxesMiddleware'
    ]

    # Mock the captcha API call
    responses.add(
        responses.POST,
        'https://www.google.com/recaptcha/api/siteverify',
        json={'success': True, 'score': 0.9},
        status=200,
    )

    signin_url = reverse('signin')
    post_data = {
        'username': 'testuser',
        'password': 'wrongpassword',
        'g-recaptcha-response': 'fake-token',
    }

    response = client.post(signin_url, post_data)

    # Assert the page is re-rendered with an error
    assert response.status_code == 200
    messages = list(response.context['messages'])
    assert len(messages) == 1
    assert str(messages[0]) == 'Invalid credentials'

    # Assert that the user is not logged in
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_signin_get_authenticated_user_is_redirected(client, client_model):
    """Test that an already authenticated user is redirected from the signin page."""
    client.force_login(client_model)
    signin_url = reverse('signin')
    response = client.get(signin_url)

    # Assert user is redirected to the rooms page
    assert response.status_code == 302
    assert response.url == reverse('rooms')
