import re
import pytest
from django.core.management import call_command
from clients.models import Client
from datetime import date
from django.urls import reverse


@pytest.fixture(scope='function')
def valid_signup_data():
    """
    Provides valid data for signup.
    """
    return {
        'username': 'test_username',
        'password': 'test_password@123',
        'nome': 'testname',
        'sobrenome': 'test lastname',
        'telefone': '27988555689',
        'nascimento': date(2003, 5, 1),
        'email': 'email@email.com',
        'cpf': '52753984093'
    }

@pytest.fixture(scope='function')
def existing_user_data(user):
    """
    Provides existing user data for signup tests.
    """
    return {
        'username': user.username,
        'password': user.password,
        'nome': user.first_name,
        'sobrenome': user.last_name,
        'telefone': user.phone,
        'nascimento': user.birthdate,
        'email': user.email,
        'cpf': user.cpf
    }


@pytest.fixture(scope='function')
def signin_urls():
    """
    Provides URLs related to signin.
    """
    return {
        'signin_url': reverse('signin'),
        'rooms_url': reverse('rooms'),
        'next_url_field_name': 'next',
    }

@pytest.fixture(scope='function')
def perfil_urls(user):
    """
    Provides URLs related to perfil.
    """
    return {
        'perfil_url': reverse('perfil', args=(user.pk,)),
        'perfil_update_url': reverse('update_perfil', args=(user.pk,)),
        'perfil_change_pw_url': reverse('update_perfil_password', args=(user.pk,)),
        'perfil_delete_url': reverse('delete_perfil', args=(user.pk,)),
        'next_url_field_name': 'next',
        'perfil_context_obj_name': 'object',
        'perfil_update_success_url': reverse('perfil', args=(user.pk,)),
        'perfil_delete_success_url': reverse('rooms'),
    }

@pytest.fixture
def valid_client_data(faker):
    """
    Provides a dictionary with valid data for creating a Client instance.
    """
    first_name = re.sub(r'[^a-zA-Z]', '', faker.first_name().split(' ')[0])
    last_name = re.sub(r'[^a-zA-Z]', '', faker.last_name().split(' ')[0])
    return {
        'username': faker.user_name(),
        'password': faker.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True),
        'first_name': first_name,
        'last_name': last_name,
        'birthdate': faker.date_of_birth(minimum_age=18, maximum_age=80),
        'email': faker.email(),
        'phone': '11999999999',
        'cpf': faker.cpf().replace('.', '').replace('-', ''),
    }

@pytest.fixture
def user(db, valid_client_data):
    """
    Provides a valid user instance.
    """
    return Client.objects.create_user(**valid_client_data)
