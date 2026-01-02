from datetime import date

import pytest
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
        'cpf': '52753984093',
    }


@pytest.fixture(scope='function')
def existing_user_data(client_model):
    """
    Provides existing user data for signup tests.
    """
    return {
        'username': client_model.username,
        'password': client_model.password,
        'nome': client_model.first_name,
        'sobrenome': client_model.last_name,
        'telefone': client_model.phone,
        'nascimento': client_model.birthdate,
        'email': client_model.email,
        'cpf': client_model.cpf,
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
def perfil_urls(client_model):
    """
    Provides URLs related to perfil.
    """
    return {
        'perfil_url': reverse('perfil', args=(client_model.pk,)),
        'perfil_update_url': reverse('update_perfil', args=(client_model.pk,)),
        'perfil_change_pw_url': reverse('update_perfil_password', args=(client_model.pk,)),
        'perfil_delete_url': reverse('delete_perfil', args=(client_model.pk,)),
        'next_url_field_name': 'next',
        'perfil_context_obj_name': 'object',
        'perfil_update_success_url': reverse('perfil', args=(client_model.pk,)),
        'perfil_delete_success_url': reverse('rooms'),
    }
