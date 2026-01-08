import pytest
from django.test import Client as DjangoClient
from django.urls import reverse
from clients.models import Client


@pytest.mark.django_db
def test_signup_get_authenticated_redirect(authenticated_client):
    """Test that authenticated users are redirected from signup page."""
    client, user = authenticated_client
    response = client.get(reverse('signup'))
    assert response.status_code == 302
    assert response.url == reverse('rooms')


@pytest.mark.django_db
def test_signup_get_unauthenticated_renders_template():
    """Test that unauthenticated users can access signup page."""
    client = DjangoClient()
    response = client.get(reverse('signup'))
    assert response.status_code == 200
    assert 'signup.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_signup_post_success(django_user_model, mock_recaptcha):
    """Test successful user registration."""
    client = DjangoClient()
    response = client.post(
        reverse('signup'),
        {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'nome': 'Test',
            'sobrenome': 'User',
            'nascimento': '1990-01-01',
            'telefone': '(11) 99999-9999',
            'cpf': '11144477735',
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 302
    assert response.url == reverse('rooms')
    assert django_user_model.objects.filter(username='testuser').exists()
    assert Client.objects.filter(username='testuser').exists()


@pytest.mark.django_db
def test_signup_post_validation_error(mock_recaptcha):
    """Test signup with validation errors."""
    client = DjangoClient()
    response = client.post(
        reverse('signup'),
        {
            'username': '',  # Invalid
            'email': 'invalid-email',
            'password': 'pass',
            'nome': 'Test',
            'sobrenome': 'User',
            'telefone': '(11) 99999-9999',
            'nascimento': '1990-01-01',
            'cpf': '11144477735',
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 200
    assert 'signup.html' in [t.name for t in response.templates]
    # Should contain form errors
    assert b'alert-danger' in response.content or b'campos n' in response.content


@pytest.mark.django_db
def test_signin_get_authenticated_redirect(authenticated_client):
    """Test that authenticated users are redirected from signin page."""
    client, user = authenticated_client
    response = client.get(reverse('signin'))
    assert response.status_code == 302
    assert response.url == reverse('rooms')


@pytest.mark.django_db
def test_signin_get_unauthenticated_renders_template():
    """Test that unauthenticated users can access signin page."""
    client = DjangoClient()
    response = client.get(reverse('signin'))
    assert response.status_code == 200
    assert 'signin.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_signin_get_with_next_parameter():
    """Test signin page stores next parameter in session."""
    client = DjangoClient()
    response = client.get(reverse('signin') + '?next=/some/path/')
    assert response.status_code == 200
    assert client.session['next_url'] == '/some/path/'


@pytest.mark.django_db
def test_signin_post_success(client_model_instance, mock_recaptcha):
    """Test successful user login."""
    client = DjangoClient()

    response = client.post(
        reverse('signin'),
        {
            'username': client_model_instance.username,
            'password': client_model_instance.raw_password,
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 302
    assert response.url == reverse('rooms')


@pytest.mark.django_db
def test_signin_post_invalid_credentials(mock_recaptcha):
    """Test login with invalid credentials."""
    client = DjangoClient()
    response = client.post(
        reverse('signin'),
        {
            'username': 'nonexistent',
            'password': 'wrongpass',
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 200
    assert 'signin.html' in [t.name for t in response.templates]
    # Should contain error message
    assert b'alert-danger' in response.content or b'Credenciais' in response.content


@pytest.mark.django_db
def test_signin_post_redirects_with_next_url(client_model_instance, mock_recaptcha):
    """Test login redirects to next_url when provided."""
    client = DjangoClient()

    # Set next_url in session
    session = client.session
    session['next_url'] = 'rooms'
    session.save()

    response = client.post(
        reverse('signin'),
        {
            'username': client_model_instance.username,
            'password': client_model_instance.raw_password,
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 302
    assert response.url == reverse('rooms')


@pytest.mark.django_db
def test_axes_locked_out_adds_message_and_redirects(mocker):
    """Test axes_locked_out function adds message and redirects."""
    from django.http import HttpRequest
    from clients.views import axes_locked_out
    import clients.feedback_messages as feedback_messages

    mock_messages = mocker.patch('django.contrib.messages.error')

    # Create a mock request with referer
    request = HttpRequest()
    request.META = {'HTTP_REFERER': '/signin/'}
    request.method = 'GET'

    response = axes_locked_out(request)
    assert response.status_code == 302
    assert response.url == '/signin/'

    # Check that error message was added
    mock_messages.assert_called_once_with(request, feedback_messages.SignIn.LOCKOUT_MESSAGE)


@pytest.mark.django_db
def test_logout_user_logs_out_and_redirects(authenticated_client):
    """Test logout_user function logs out user and redirects."""
    client, user = authenticated_client
    # Verify user is logged in
    assert client.session.get('_auth_user_id')

    response = client.get(reverse('logout'))
    assert response.status_code == 302
    assert response.url == reverse('signin')

    # Check that user is logged out
    client.get('/')  # Refresh session
    assert not client.session.get('_auth_user_id')


@pytest.mark.django_db
def test_perfil_detail_view_own_profile(authenticated_client):
    """Test viewing own profile details."""
    client, user = authenticated_client
    response = client.get(reverse('perfil', kwargs={'pk': user.pk}))
    assert response.status_code == 200
    assert 'perfil.html' in [t.name for t in response.templates]
    assert user.username in response.content.decode()


@pytest.mark.django_db
def test_perfil_detail_view_other_profile_forbidden(
    authenticated_client, client_model_instance_factory
):
    """Test that users cannot view other users' profiles."""
    client, user = authenticated_client
    other_user = client_model_instance_factory()
    # Try to access another user's profile
    response = client.get(reverse('perfil', kwargs={'pk': other_user.pk}))
    assert response.status_code == 403  # Forbidden


@pytest.mark.django_db
def test_perfil_update_get_renders_form(authenticated_client):
    """Test perfil update GET request renders form."""
    client, user = authenticated_client
    response = client.get(reverse('update_perfil', kwargs={'pk': user.pk}))
    assert response.status_code == 200
    assert 'perfil_update.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_perfil_update_post_success(authenticated_client, mock_recaptcha):
    """Test successful profile update."""
    client, user = authenticated_client
    response = client.post(
        reverse('update_perfil', kwargs={'pk': user.pk}),
        {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': user.phone,
            'birthdate': user.birthdate.strftime('%Y-%m-%d'),
            'cpf': user.cpf,
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 302
    assert response.url == reverse('perfil', kwargs={'pk': user.pk})

    # Refresh user from database
    user.refresh_from_db()
    assert user.username == 'updateduser'
    assert user.email == 'updated@example.com'


@pytest.mark.django_db
def test_perfil_update_other_profile_forbidden(
    authenticated_client, client_model_instance_factory
):
    """Test that users cannot update other users' profiles."""
    client, user = authenticated_client
    other_user = client_model_instance_factory()
    response = client.post(
        reverse('update_perfil', kwargs={'pk': other_user.pk}),
        {
            'username': 'hacked',
            'email': 'hacked@example.com',
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_perfil_change_password_get_renders_form(authenticated_client):
    """Test password change GET request renders form."""
    client, user = authenticated_client
    response = client.get(reverse('update_perfil_password', kwargs={'pk': user.pk}))
    assert response.status_code == 200
    assert 'perfil_update_password.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_perfil_change_password_post_success(authenticated_client, mock_recaptcha):
    """Test successful password change."""
    client, user = authenticated_client
    new_password = 'newpassword123'

    response = client.post(
        reverse('update_perfil_password', kwargs={'pk': user.pk}),
        {
            'new_password': new_password,
            'password_repeat': new_password,
            'g-recaptcha-response': 'mocked_response',
        },
    )
    assert response.status_code == 302
    assert response.url == reverse('perfil', kwargs={'pk': user.pk})

    # Verify password was changed
    user.refresh_from_db()
    assert user.check_password(new_password)


@pytest.mark.django_db
def test_perfil_delete_get_renders_confirmation(authenticated_client):
    """Test profile delete GET request renders confirmation."""
    client, user = authenticated_client
    response = client.get(reverse('delete_perfil', kwargs={'pk': user.pk}))
    assert response.status_code == 200
    assert 'perfil_delete.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_perfil_delete_post_success(authenticated_client, mock_recaptcha):
    """Test successful profile deletion."""
    client, user = authenticated_client
    user_pk = user.pk

    response = client.post(
        reverse('delete_perfil', kwargs={'pk': user.pk}),
        {'g-recaptcha-response': 'mocked_response'},
    )
    assert response.status_code == 302
    assert response.url == reverse('rooms')

    # Verify user was deleted
    with pytest.raises(Client.DoesNotExist):
        Client.objects.get(pk=user_pk)


@pytest.mark.django_db
def test_perfil_delete_other_profile_forbidden(
    authenticated_client, client_model_instance_factory
):
    """Test that users cannot delete other users' profiles."""
    client, user = authenticated_client
    other_user = client_model_instance_factory()
    response = client.post(
        reverse('delete_perfil', kwargs={'pk': other_user.pk}),
        {'g-recaptcha-response': 'mocked_response'},
    )
    assert response.status_code == 403
