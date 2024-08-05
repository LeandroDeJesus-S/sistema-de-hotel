from datetime import date
from http import HTTPStatus

from django.core.management import call_command
from django.http import HttpResponseForbidden
from django.test import TestCase
from django.urls import reverse

from clients.models import Client
from utils.supportmodels import ClientErrorMessages, ClientRules, ContactErrorMessages
from utils.supporttest import get_message
from utils.supportviews import SignUpMessages, SignInMessages, PerfilChangePasswordMessages
from reservations.models import Room


class BaseTestClient(TestCase):
    def setUp(self) -> None:
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')

        self.user = Client.objects.get(pk=1)
        
        self.signup_teamplate = 'signup.html'
        self.signin_template = 'signin.html'
        self.perfil_template = 'perfil.html'
        self.perfil_update_template = 'perfil_update.html'
        self.perfil_change_pw_template = 'perfil_update_password.html'
        self.perfil_delete_template = 'perfil_delete.html'

        self.signin_url = reverse('signin')
        self.signup_url = reverse('signup')
        self.logout_url = reverse('logout')
        self.rooms_url = reverse('rooms')
        self.perfil_url = reverse('perfil', args=(self.user.pk,))
        self.perfil_update_url = reverse('update_perfil', args=(self.user.pk,))
        self.perfil_change_pw_url = reverse('update_perfil_password', args=(self.user.pk,))
        self.perfil_delete_url = reverse('delete_perfil', args=(self.user.pk,))

        self.next_url_field_name = 'next'
        self.perfil_context_obj_name = 'object'
        self.perfil_update_sucess_url = self.perfil_url
        self.perfil_delete_success_url = self.rooms_url


class TestSignUp(BaseTestClient):
    def setUp(self):
        super().setUp()
        self.valid_data = {
            'username': 'test_username',
            'password': 'test_password@123',
            'nome': 'testname',
            'sobrenome': 'test lastname',
            'telefone': '27988555689',
            'nascimento': date(2003, 5, 1),
            'email': 'email@email.com',
            'cpf': '52753984093'
        }

        self.exinting_user_data = {
            'username': self.user.username,
            'password': self.user.password,
            'nome': self.user.first_name,
            'sobrenome': self.user.last_name,
            'telefone': self.user.phone,
            'nascimento': self.user.birthdate,
            'email': self.user.email,
            'cpf': self.user.cpf
        }

    def test_template(self):
        """testa se esta renderiando o template correto"""
        response = self.client.get(reverse('signup'))
        self.assertTemplateUsed(response, self.signup_teamplate)

    def test_se_tiver_campo_missing_renderiza_novamente_signup_com_mensagem(self):
        """testa se ao passar alguma informação faltante envia a msg
        correta e renderiza novamente o template signup.html
        """
        for k in self.valid_data.keys():
            self.valid_data[k] = ''
            with self.subTest(field=k):
                response = self.client.post(reverse('signup'), self.valid_data)
                msg = get_message(response)
                self.assertEqual(msg, SignUpMessages.MISSING)
                self.assertTemplateUsed(response, self.signup_teamplate)

    def test_usuario_usando_dados_existententes_para_campos_unicos_renderiza_novamente_signup_com_mensagem_correta(self):
        """testa se campos que devem ser unicos são validados corretamente renderizando novamente
        signup com mensagem correta
        """
        cases = [
            ('username', ClientErrorMessages.DUPLICATED_USERNAME),
            ('telefone', ContactErrorMessages.DUPLICATED_PHONE),
            ('email', ContactErrorMessages.DUPLICATED_EMAIL),
            ('cpf', ClientErrorMessages.DUPLICATED_CPF),
        ]
        for field, expected_msg in cases:
            data = self.valid_data.copy()
            data[field] = self.exinting_user_data[field]
            with self.subTest(field=field, expected_msg=expected_msg, data=data):
                response = self.client.post(reverse('signup'), data)
                msg = get_message(response)
                self.assertTemplateUsed(response, self.signup_teamplate)
                self.assertEqual(msg, expected_msg)
    
    def test_username_invalido_renderiza_signup_com_mensagem_correta(self):
        """testa se ao usar um username invalido renderiza novamente a pagina
        de signup com a mensagem correspondente valida
        """
        cases = {
            ('invalid_min_lengh', '1' * (ClientRules.USERNAME_MIN_SIZE - 1), ClientErrorMessages.INVALID_USERNAME_LEN),
            ('invalid_max_lengh', '1' * (ClientRules.USERNAME_MAX_SIZE + 1), ClientErrorMessages.INVALID_USERNAME_LEN),
            ('only_numbers_sent', '12345678', ClientErrorMessages.INVALID_USERNAME_CHARS),
            ('invalid_invalid_sharp_char_used', 'dah#1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
            ('invalid_invalid_dolar_char_used', 'dah$1234', ClientErrorMessages.INVALID_USERNAME_CHARS),
        }
        for case_key, case_value, case_message in cases:
            with self.subTest(case_key=case_key, case_value=case_value, case_message=case_message):
                self.valid_data['username'] = case_value
                response = self.client.post(self.signup_url, self.valid_data)
                msg = get_message(response)

                self.assertTemplateUsed(response, self.signup_teamplate)
                self.assertEqual(msg, case_message)
    
    def test_cliente_e_logado_se_tudo_valido(self):
        """testa se o cliente é logado corretamente quando todos
        os dados fornecidos são validos
        """
        response = self.client.post(self.signup_url, self.valid_data)
        result = response.wsgi_request.user.is_authenticated
        self.assertTrue(result)
    
    def test_cliente_vai_para_signup_ja_estando_logado_e_redirecionado_para_pagina_de_quartos(self):
        """testa se um cliente que ja esta logado e tenta acessar a pagina de signup
        é redirecionado para a pagina de quartos
        """
        self.client.force_login(self.user)
        response = self.client.get(self.signup_url)
        self.assertRedirects(response, reverse('rooms'), status_code=HTTPStatus.FOUND)

    def test_login_com_username(self):
        """testa se o usuario consegue realizar o login com username
        corretamente
        """
        userpass = self.user.password
        self.user.set_password(self.user.password)
        self.user.save()

        result = self.client.login(username=self.user.username, password=userpass)
        self.assertTrue(result)
    
    def test_login_com_email(self):
        """testa se o usuario consegue realizar o login usando o email
        ao invés do username.
        """
        userpass = self.user.password
        self.user.set_password(self.user.password)
        self.user.save()

        result = self.client.login(username=self.user.email, password=userpass)
        self.assertTrue(result)


class TestSignIn(BaseTestClient):
    def setUp(self) -> None:
        super().setUp()
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')

        self.room = Room.objects.get(pk=1)
        self.reserve_url = reverse('reserve', args=(self.room.pk,))
    
    def _signin(self, url=None, username='', password=''):
        """persiste o hash da senha do usuario e manda um solicitação
        post para signin
        """
        if url is None:
            url = self.signin_url

        self.user.set_password(self.user.password)
        self.user.save()

        response = self.client.post(url, {'username': username, 'password': password})
        return response
    
    def test_template(self):
        """testa se signin renderiza o template correto"""
        response = self.client.get(self.signin_url)
        self.assertTemplateUsed(response, self.signin_template)
    
    def test_cliente_ja_logado_e_redirecionado_para_quarto(self):
        """testa se cliente ja logado é redirecionado para a pagina de 
        quartos ao tentar acessar singin
        """
        self.client.force_login(self.user)
        response = self.client.get(self.signin_url)
        self.assertRedirects(response, self.rooms_url, status_code=HTTPStatus.FOUND)
    
    def test_cliente_e_logado_se_username_e_senha_sao_validos(self):
        """testa se usuario é logado corretamente via username e senha
        sendo eles validos
        """
        response = self._signin(self.signin_url, self.user.username, self.user.password)
        result = response.wsgi_request.user.is_authenticated
        self.assertTrue(result)
    
    def test_cliente_e_logado_com_email_e_senha_validos(self):
        """testa se usuario é logado corretamente usando email e senha
        validos
        """
        response = self._signin(self.signin_url, self.user.username, self.user.password)
        result = response.wsgi_request.user.is_authenticated
        self.assertTrue(result)
    
    def test_cliente_e_redirecionado_para_quartos_quando_logado(self):
        """testa se apos realizar o login o cliente é redirecionado para os
        quartos
        """
        response = self._signin(self.signin_url, self.user.username, self.user.password)
        self.assertRedirects(response, self.rooms_url, status_code=HTTPStatus.FOUND)
    
    def _invalid_credentials_cases(self):
        """retorna uma lista de casos de crendencias invalidas"""
        cases = [
            ('invalid_password_with_valid_username', self.user.username, 'invalid_password'),
            ('invalid_username_with_valid_password', 'invalid_username', self.user.password),
            ('invalid_password_with_valid_email', self.user.email, 'invalid_password'),
        ]
        return cases

    def test_cliente_com_credenciais_invalidas_renderiza_novamente_signin_com_mensagem_correta(self):
        """testa se quando as credencias fornecidas forem invalidas renderiza
        novamente a página de signin com a mensagem correta.
        """
        for case_id, case_username, case_pw in self._invalid_credentials_cases():
            with self.subTest(case_id=case_id, case_username=case_username, case_pw=case_pw):
                response = self._signin(self.signin_url, case_username, case_pw)
                msg = get_message(response)

                self.assertTemplateUsed(response, self.signin_template)
                self.assertEqual(msg, SignInMessages.INVALID_CREDENTIALS)
    
    def test_cliente_nao_logado_e_redirecionado_para_signin_com_field_de_next_url_se_tentar_fazer_reserva(self):
        """testa se ao tentar fazer reserva sem estar logado o cliente é redirecionado
        para sigin com argumento de proxima url para redirect
        """
        next_url = self.reserve_url
        url = self.signin_url + f'?{self.next_url_field_name}={next_url}'

        response = self.client.get(next_url)
        self.assertRedirects(response, url, status_code=HTTPStatus.FOUND)
    
    def test_cliente_redirecionado_para_login_ao_tentar_fazer_reserva_e_redirecionado_para_continuar_reserva_apos_logado(self):
        """testa se apos tentar fazer reserva sem estar logado, ser redirecionado
        para signin e completar o login o cliente é redirecionado para a pagina de
        reserva
        """
        next_url = self.reserve_url
        url = reverse('signin') + f'?next={next_url}'

        pw = self.user.password
        self.user.set_password(pw)
        data = {'username': self.user.username, 'password': pw}

        response = self.client.get(next_url)
        response = response.client.post(response.wsgi_request.path, data)
        self.assertRedirects(response, url)
    
    def _missing_credential_cases(self):
        """retorna casos de credenciasi faltantes"""
        cases = [
            ('username_missing_com_password_valida', '', self.user.password),
            ('password_missing_com_username_valido', self.user.username, ''),
            ('password_missing_com_email_valido', self.user.email, ''),
        ]
        return cases
    
    def test_se_usuario_passar_credencias_faltantes_renderiza_novamente_sigin_com_mensagem_correta(self):
        """testa se ao não passar todas as credencias necessarias rederiza
        novamente a pagina de signin com mensagem"""
        for case_id, case_username, case_pw in self._missing_credential_cases():
            with self.subTest(case_id=case_id, case_username=case_username, case_pw=case_pw):
                response = self._signin(username=case_username, password=case_pw)
                msg = get_message(response)

                self.assertTemplateUsed(response, self.signin_template)
                self.assertEqual(msg, SignInMessages.INVALID_CREDENTIALS)
    
    def test_next_url_e_deletado_da_session_apos_capiturado_no_post(self):
        """testa se apos a capitura de next_url via sesion no metodo post
        ele é retirado da session
        """
        next_url = self.reserve_url
        url = self.signin_url + f'?next={next_url}'

        pw = self.user.password
        self.user.set_password(pw)
        data = {'username': self.user.username, 'password': pw}

        response = self.client.get(next_url)
        response = response.client.post(self.signin_url, data)

        result = response.client.session.has_key('next_url')
        self.assertFalse(result)


class TestLogout(BaseTestClient):
    def test_usuario_logado_e_deslogado(self):
        """testa se um usuario logado é deslogado como esperado"""
        self.client.force_login(self.user)
        response = self.client.get(self.logout_url)
        
        result = response.wsgi_request.user.is_authenticated
        self.assertFalse(result)
    
    def test_usuario_deslogado_redirecionado_para_signin(self):
        """testa se apos deslogado o usario é redirecionado para signin"""
        self.client.force_login(self.user)
        response = self.client.get(self.logout_url)

        self.assertRedirects(response, reverse('signin'))
    
    def test_usuario_nunca_logado_redirecionado_para_signin(self):
        """testa se um usuario que não esta logado tentando acessar
        logout é redirecionado para signin
        """
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.signin_url, status_code=HTTPStatus.FOUND)


class TestPerfil(BaseTestClient):
    def _log_user(self):
        self.client.force_login(self.user)

    def test_template(self):
        """testa se renderiza o template perfil.html"""
        self._log_user()
        response = self.client.get(self.perfil_url)
        self.assertTemplateUsed(response, self.perfil_template)

    def test_dados_de_cliente_correto_e_mostrado(self):
        """testa os perfil que esta sendo mostrado é o perfil
        correto do cliente
        """
        self._log_user()
        response = self.client.get(self.perfil_url)
        perfil = response.context[self.perfil_context_obj_name]
        self.assertEqual(perfil, self.user)
    
    def test_cliente_deslogado_e_redirecionado_para_signin(self):
        """testa se cliente tentar acessar perfil não estando logado
        é redirecionado para pagina de login
        """
        response = self.client.get(self.perfil_url)
        next_url = reverse('signin') + f'?{self.next_url_field_name}={self.perfil_url}'
        self.assertRedirects(response, next_url, status_code=HTTPStatus.FOUND)

    def test_cliente_tentando_acessar_perfil_que_nao_e_dele_rece_http_forbiden(self):
        """testa se o cliente tentar acessar um perfil que não seja o dele sera
        recebido um erro 403 http forbiden
        """
        self._log_user()
        response = self.client.get(self.perfil_url.replace('1', '2'))
        self.assertIsInstance(response, HttpResponseForbidden)


class TestPerfilUpdate(BaseTestClient):
    def test_template(self):
        """testa se renderiza o template perfil_update.html como esperado"""
        self.client.force_login(self.user)
        response = self.client.get(self.perfil_update_url)
        self.assertTemplateUsed(response, self.perfil_update_template)

    def test_cliente_nao_logado_e_redirecionado_para_signin(self):
        """testa se usuario é redirecionado para fazer login caso 
        tente alterar o perfil sem estar logado
        """
        response = self.client.get(self.perfil_update_url)
        expected_url = reverse('signin') + f'?{self.next_url_field_name}={self.perfil_update_url}'
        self.assertRedirects(response, expected_url, status_code=HTTPStatus.FOUND)

    def test_se_cliente_logado_tenta_acessar_update_perfil_de_outro_cliente_recebe_http_forbiden(self):
        """testa se um cliente tentar acessar a pagina de alterar dados de outro ele recebe
        http forbiden
        """
        self.client.force_login(self.user)
        response = self.client.get(
            self.perfil_update_url.replace('1', '2'),
        )
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_se_cliente_logado_tenta_alterar_perfil_de_outro_cliente_recebe_http_forbiden(self):
        """testa se um cliente tentar alterar dados de outro ele recebe
        http forbiden
        """
        self.client.force_login(self.user)
        response = self.client.post(
            self.perfil_update_url.replace('1', '2'),
            data={
                'username': 'new username',
            }
        )
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_cliente_altera_os_dados_corretamente_se_tudo_ocorrer_como_esperado(self):
        """testa se um cliente logado consegue alterar seus dados corretamente
        como esperado.
        """
        self.client.force_login(self.user)
        new_email = 'updated@email.com'
        new_username = 'udpatedusername'
        data = {
            'username': new_username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'phone': self.user.phone,
            'email': new_email,
            'birthdate': self.user.birthdate,
            'cpf': self.user.cpf
        }
        self.client.post(self.perfil_update_url, data=data)
        user = Client.objects.get(pk=self.user.pk)
        self.assertListEqual([user.email, user.username], [new_email, new_username])

    def test_cliente_nao_consegue_alterar_senha_em_perfil_update(self):
        """testa se o cliente tentar enviar uma nova senha ela nao é
        persistida no banco de dados
        """
        self.client.force_login(self.user)
        data = {
            'username': self.user.username,
            'password': 'novasenha@123',
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'phone': self.user.phone,
            'email': self.user.email,
            'birthdate': self.user.birthdate,
            'cpf': self.user.cpf
        }
        self.client.post(self.perfil_update_url, data=data)
        user = Client.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('novasenha@123'))


class TestPerfilChangePassword(BaseTestClient):
    def setUp(self) -> None:
        super().setUp()
        self.data = {'new_password': 'novasenha@01', 'password_repeat': 'novasenha@01'}
    
    def test_template(self):
        """testa se esta renderizando o template perfil_update_password.html"""
        self.client.force_login(self.user)
        response = self.client.get(self.perfil_change_pw_url)
        self.assertTemplateUsed(response, self.perfil_change_pw_template)
    
    def test_cliente_nao_logado_nao_consegue_acessar_pagina_de_alterar_senha(self):
        """testa se o cliente nao logado é solicitado para fazer login
        antes de acessar pagina de update da senha
        """
        response = self.client.get(self.perfil_change_pw_url)
        next_url = reverse('signin') + f'?{self.next_url_field_name}={self.perfil_change_pw_url}'
        self.assertRedirects(response, next_url, status_code=HTTPStatus.FOUND)

    def test_cliente_logado_nao_consegue_alterar_senha_de_outro_cliente(self):
        """testa se o cliente logado tentar alterar senha de outro ele recebe
        http forbiden
        """
        self.client.force_login(self.user)

        response = self.client.post(self.perfil_change_pw_url.replace('1', '2'), self.data)
        self.assertIsInstance(response, HttpResponseForbidden)
        other = Client.objects.get(pk=2)
        self.assertFalse(other.check_password('novasenha@01'))

    def test_senhas_diferentes_nao_passam_por_validacao_e_redireciona_para_o_perfil(self):
        """se o cliente não enviar senha identicas a validação não prossegue
        e redireciona para a página do perfil
        """
        self.client.force_login(self.user)
        self.data['password_repeat'] = self.data['password_repeat'].title()
        response = self.client.post(self.perfil_change_pw_url, self.data)
        self.assertRedirects(response, self.perfil_url, status_code=HTTPStatus.FOUND)

    def test_mensagem_quando_senhas_diferem(self):
        """testa se a mensagem de senhas diferentes é a correta
        """
        self.client.force_login(self.user)
        self.data['password_repeat'] = self.data['password_repeat'].title()
        response = self.client.post(self.perfil_change_pw_url, self.data)
        msg = get_message(response)
        self.assertEqual(msg, PerfilChangePasswordMessages.PASSWORDS_DIFFERS)

    def test_mensagem_quando_senhas_e_alterada_com_sucesso(self):
        """testa se a mensagem de senha alterada é a correta
        """
        self.client.force_login(self.user)
        response = self.client.post(self.perfil_change_pw_url, self.data)
        msg = get_message(response)
        self.assertEqual(msg, PerfilChangePasswordMessages.SUCCESS)

    def test_senha_e_persistida_corretamente_no_banco(self):
        """testa se a senha é persistida de forma valida no banco de dados
        """
        self.client.force_login(self.user)
        response = self.client.post(self.perfil_change_pw_url, self.data)
        msg = get_message(response)
        saved = Client.objects.get(pk=self.user.pk)
        self.assertTrue(saved.check_password(self.data['new_password']))


class TestPerfilDelete(BaseTestClient):
    def test_template(self):
        """testa se renderiza o template correto"""
        self.client.force_login(self.user)
        response = self.client.get(self.perfil_delete_url)
        self.assertTemplateUsed(response, self.perfil_delete_template)
    
    def test_cliente_nao_logado_nao_consegue_acessar_delete_perfil(self):
        """cliente não consegue acessar pagina de deletar perfil caso
        não esteja autenticado.
        """
        response = self.client.get(self.perfil_delete_url)
        next_url = reverse('signin') + f'?{self.next_url_field_name}={self.perfil_delete_url}'
        self.assertRedirects(response, next_url)
    
    def test_cliente_logado_nao_consegue_deletar_perfil_de_outro_recebendo_403(self):
        """testa se o cliente não é capaz de acessar pagina de deletar o 
        perfil de outro cliente recebendo http forbiden
        """
        self.client.force_login(self.user)
        response = self.client.get(self.perfil_delete_url.replace('1', '2'))
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_cliente_logado_nao_consegue_deletar_perfil_de_outro_recebendo_403(self):
        """testa se o cliente não é capaz de deletar o perfil de outro
        cliente recebendo http forbiden
        """
        self.client.force_login(self.user)
        response = self.client.post(self.perfil_delete_url.replace('1', '2'))
        self.assertIsInstance(response, HttpResponseForbidden)
    
    def test_success_url(self):
        """testa se redireciona para a url correta após excluir o perfil"""
        self.client.force_login(self.user)
        response = self.client.post(self.perfil_delete_url)
        self.assertRedirects(response, self.perfil_delete_success_url)

    def test_cliente_e_deletado_se_tudo_ocorrer_como_esperado(self):
        """testa a exclusao de um cliente se tudo ocorrer como devido"""
        self.client.force_login(self.user)
        self.client.post(self.perfil_delete_url)
        with self.assertRaises(Client.DoesNotExist):
            Client.objects.get(pk=self.user.pk)
