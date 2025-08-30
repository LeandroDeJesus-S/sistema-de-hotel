# """Clients views tests."""

# from datetime import date
# from http import HTTPStatus

# import pytest
# from django.core.management import call_command
# from django.test import override_settings
# from django.urls import reverse

# from clients.models import Client
# from utils.supportmodels import ClientErrorMessages, ClientRules, ContactErrorMessages
# from utils.supporttest import get_message
# from utils.supportviews import PerfilChangePasswordMessages, SignInMessages, SignUpMessages


# @pytest.mark.django_db
# def test_signup_template(client):
#     """Test if it is rendering the correct template."""
#     # Arrange
#     url = reverse('signup')

#     # Act
#     response = client.get(url)

#     # Assert
#     assert 'signup.html' in [t.name for t in response.templates]


# @pytest.mark.parametrize(
#     'field',
#     [
#         'username',
#         'password',
#         'nome',
#         'sobrenome',
#         'telefone',
#         'nascimento',
#         'email',
#         'cpf',
#     ],
# )
# @pytest.mark.django_db
# def test_signup_missing_field_renders_signup_with_message(
#     mocker,
#     client,
#     valid_signup_data,
#     field,
# ):
#     """
#     Test if when sending some missing information, the correct message is sent.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')
#     data = valid_signup_data.copy()
#     data[field] = ''

#     # Act
#     response = client.post(url, data)
#     message = get_message(response)

#     # Assert
#     assert message == SignUpMessages.MISSING


# @pytest.mark.parametrize(
#     'field',
#     [
#         'username',
#         'password',
#         'nome',
#         'sobrenome',
#         'telefone',
#         'nascimento',
#         'email',
#         'cpf',
#     ],
# )
# @pytest.mark.django_db
# def test_signup_missing_field_renders_correct_template(
#     mocker,
#     client,
#     valid_signup_data,
#     field,
# ):
#     """Test if when sending some missing information, the correct template is rendered."""
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')
#     data = valid_signup_data.copy()
#     data[field] = ''

#     # Act
#     response = client.post(url, data)

#     # Assert
#     assert 'signup.html' in [t.name for t in response.templates]


# @pytest.mark.parametrize(
#     ('field', 'expected_msg'),
#     [
#         ('username', ClientErrorMessages.DUPLICATED_USERNAME),
#         ('telefone', ContactErrorMessages.DUPLICATED_PHONE),
#         ('email', ContactErrorMessages.DUPLICATED_EMAIL),
#         ('cpf', ClientErrorMessages.DUPLICATED_CPF),
#     ],
# )
# @pytest.mark.django_db
# def test_signup_duplicated_unique_field_renders_signup_with_message(
#     mocker,
#     client,
#     valid_signup_data,
#     existing_user_data,
#     field,
#     expected_msg,
# ):
#     """
#     Test if fields that must be unique are validated correctly,
#     rendering signup again with the correct message.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')
#     data = valid_signup_data.copy()
#     data[field] = existing_user_data[field]
#     print(data)
#     # Act
#     response = client.post(url, data)
#     message = get_message(response)

#     # Assert
#     assert message == expected_msg


# @pytest.mark.parametrize(
#     ('field', 'expected_msg'),
#     [
#         ('username', ClientErrorMessages.DUPLICATED_USERNAME),
#         ('telefone', ContactErrorMessages.DUPLICATED_PHONE),
#         ('email', ContactErrorMessages.DUPLICATED_EMAIL),
#         ('cpf', ClientErrorMessages.DUPLICATED_CPF),
#     ],
# )
# @pytest.mark.django_db
# def test_signup_duplicated_unique_field_renders_correct_template(
#     mocker,
#     client,
#     valid_signup_data,
#     existing_user_data,
#     field,
#     expected_msg,
# ):
#     """
#     Test if fields that must be unique are validated correctly,
#     rendering signup again with the correct template.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')
#     data = valid_signup_data.copy()
#     data[field] = existing_user_data[field]

#     # Act
#     response = client.post(url, data)

#     # Assert
#     assert 'signup.html' in [t.name for t in response.templates]


# @pytest.mark.parametrize(
#     ('case_value', 'case_message'),
#     [
#         (
#             '1' * (ClientRules.USERNAME_MIN_SIZE - 1),
#             ClientErrorMessages.INVALID_USERNAME_LEN,
#         ),
#         (
#             '1' * (ClientRules.USERNAME_MAX_SIZE + 1),
#             ClientErrorMessages.INVALID_USERNAME_LEN,
#         ),
#         ('12345678', ClientErrorMessages.INVALID_USERNAME_CHARS),
#         ('dah#1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
#         ('dah$1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
#     ],
# )
# @pytest.mark.django_db
# def test_signup_invalid_username_renders_signup_with_message(
#     mocker,
#     client,
#     valid_signup_data,
#     case_value,
#     case_message,
# ):
#     """
#     Test if using an invalid username renders the signup page
#     again with the corresponding valid message.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')
#     data = valid_signup_data.copy()
#     data['username'] = case_value

#     # Act
#     response = client.post(url, data)
#     message = get_message(response)

#     # Assert
#     assert message == case_message


# @pytest.mark.parametrize(
#     ('case_value', 'case_message'),
#     [
#         (
#             '1' * (ClientRules.USERNAME_MIN_SIZE - 1),
#             ClientErrorMessages.INVALID_USERNAME_LEN,
#         ),
#         (
#             '1' * (ClientRules.USERNAME_MAX_SIZE + 1),
#             ClientErrorMessages.INVALID_USERNAME_LEN,
#         ),
#         ('12345678', ClientErrorMessages.INVALID_USERNAME_CHARS),
#         ('dah#1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
#         ('dah$1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
#     ],
# )
# @pytest.mark.django_db
# def test_signup_invalid_username_renders_correct_template(
#     mocker,
#     client,
#     valid_signup_data,
#     case_value,
#     case_message,
# ):
#     """
#     Test if using an invalid username renders the signup page
#     again with the corresponding valid template.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')
#     data = valid_signup_data.copy()
#     data['username'] = case_value

#     # Act
#     response = client.post(url, data)

#     # Assert
#     assert 'signup.html' in [t.name for t in response.templates]


# @pytest.mark.parametrize(
#     ('case_value', 'case_message'),
#     [
#         (
#             '1' * (ClientRules.USERNAME_MIN_SIZE - 1),
#             ClientErrorMessages.INVALID_USERNAME_LEN,
#         ),
#         (
#             '1' * (ClientRules.USERNAME_MAX_SIZE + 1),
#             ClientErrorMessages.INVALID_USERNAME_LEN,
#         ),
#         ('12345678', ClientErrorMessages.INVALID_USERNAME_CHARS),
#         ('dah#1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
#         ('dah$1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
#     ],
# )
# @pytest.mark.django_db
# def test_signup_invalid_username_renders_correct_template(
#     mocker,
#     client,
#     valid_signup_data,
#     case_value,
#     case_message,
# ):
#     """
#     Test if using an invalid username renders the signup page
#     again with the corresponding valid template.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')
#     data = valid_signup_data.copy()
#     data['username'] = case_value

#     # Act
#     response = client.post(url, data)

#     # Assert
#     assert 'signup.html' in [t.name for t in response.templates]


# @override_settings(AUTHENTICATION_BACKENDS=['clients.authenticator.UserEmailAuthBackend'])
# @pytest.mark.django_db
# def test_signup_valid_data_authenticates_user(mocker, client, valid_signup_data):
#     """
#     Test if the client is logged in correctly when all data provided is valid.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=True)
#     url = reverse('signup')

#     # Act
#     response = client.post(url, valid_signup_data)

#     # Assert
#     assert response.wsgi_request.user.is_authenticated


# def test_signup_authenticated_user_is_redirected(authenticated_client):
#     """
#     Test if a client who is already logged in and tries to access
#     the signup page is redirected to the rooms page.
#     """
#     # Arrange
#     client, _ = authenticated_client
#     url = reverse('signup')

#     # Act
#     response = client.get(url)

#     # Assert
#     assert response.status_code == HTTPStatus.FOUND


# def test_signup_authenticated_user_is_redirected_to_rooms(authenticated_client):
#     """
#     Test if a client who is already logged in and tries to access
#     the signup page is redirected to the rooms page.
#     """
#     # Arrange
#     client, _ = authenticated_client
#     url = reverse('signup')

#     # Act
#     response = client.get(url)

#     # Assert
#     assert response.url == reverse('rooms')


# @override_settings(AUTHENTICATION_BACKENDS=['clients.authenticator.UserEmailAuthBackend'])
# @pytest.mark.django_db
# def test_login_with_username(client, user):
#     """Test if the user can successfully log in with a username."""
#     # Arrange
#     password = user.password
#     user.set_password(password)
#     user.save()

#     # Act
#     result = client.login(username=user.username, password=password)

#     # Assert
#     assert result


# @override_settings(AUTHENTICATION_BACKENDS=['clients.authenticator.UserEmailAuthBackend'])
# @pytest.mark.django_db
# def test_login_with_email(client, user):
#     """
#     Test if the user can log in using email instead of username.
#     """
#     # Arrange
#     password = user.password
#     user.set_password(password)
#     user.save()

#     # Act
#     result = client.login(username=user.email, password=password)

#     # Assert
#     assert result


# @pytest.mark.django_db
# def test_signup_invalid_captcha_redirects_to_signup_with_message(
#     mocker,
#     client,
#     valid_signup_data,
# ):
#     """
#     Test if the captcha is invalid, redirect back to the registration
#     page with the correct message.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=False)
#     url = reverse('signup')

#     # Act
#     response = client.post(url, valid_signup_data)
#     message = get_message(response)

#     # Assert
#     assert message == 'Mr. Robot, é você???'


# @pytest.mark.django_db
# def test_signup_invalid_captcha_redirects_to_signup(mocker, client, valid_signup_data):
#     """
#     Test if the captcha is invalid, redirect back to the registration page.
#     """
#     # Arrange
#     mocker.patch('clients.views.support.verify_captcha', return_value=False)
#     url = reverse('signup')

#     # Act
#     response = client.post(url, valid_signup_data)

#     # Assert
#     assert response.url == url
