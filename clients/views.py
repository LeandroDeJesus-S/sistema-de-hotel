import logging
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import DeleteView, UpdateView

from clients.application.usecases_value_objects import ChangePasswordInput
from clients.models import Client
from reservations.mixins import LoginRequired
from utils import support

from .application.services import ClientService
from .decorators import profile_ownership_required
from .domain.entities import Client as DomainClient
from .error_messages import (
    PerfilChangePasswordMessages,
    SignUpMessages,
)
from .forms import UpdatePerfilForm
from .infra.adapters import (
    DjangoPasswordManager,
    DjangoSessionManager,
    GoogleRecaptchaV3Verifier,
)
from .infra.repo import ClientRepository

CAPTCHA_CTX = {'recaptcha_site_key': settings.G_RECAPTCHA_KEY_SITE}


@method_decorator(support.captcha_required('signup'), name='post')
class SignUp(View):
    """View responsável por realizar o registro de novos usuários"""

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template_name = 'signup.html'
        self._redirect = redirect('rooms')
        self.svc = ClientService(
            repo=ClientRepository(),
            password_manager=DjangoPasswordManager(),
            session_manager=DjangoSessionManager(),
            captcha_service=GoogleRecaptchaV3Verifier(settings.G_RECAPTCHA_KEY_SECRET),
        )

    def get(self, request):
        if request.user.is_authenticated:
            self.logger.info(f'user already logged in. Redirecting to {self._redirect.url}')
            return self._redirect

        return render(request, self.template_name, CAPTCHA_CTX)

    def post(self, request: HttpRequest):
        username = self.request.POST.get('username', '').strip()
        password = self.request.POST.get('password')
        name = self.request.POST.get('nome', '').strip()
        surname = self.request.POST.get('sobrenome', '').strip()
        phone = self.request.POST.get('telefone', '').strip()
        email = self.request.POST.get('email', '').strip()
        birthdate = self.request.POST.get('nascimento')
        cpf = self.request.POST.get('cpf', '').strip()

        if not all((
            username,
            password,
            name,
            surname,
            phone,
            email,
            birthdate,
            cpf,
        )):
            messages.error(request, SignUpMessages.MISSING_FIELDS)
            return render(request, self.template_name, CAPTCHA_CTX)

        client_entity, err = DomainClient.safe_create(
            username=username,
            password=password,
            first_name=name,
            last_name=surname,
            phone=phone,
            birthdate=birthdate,
            email=email,
            cpf=cpf,
        )
        if err:
            messages.error(request, err.msg)
            self.logger.error(str(err))
            return render(request, self.template_name, CAPTCHA_CTX)

        if client_entity is None:
            messages.error(request, 'Unexpected error occurred. Please try again.')
            self.logger.error('client entity is None after creation')
            return render(request, self.template_name, CAPTCHA_CTX)

        created_user_result = self.svc.create_user(client_entity)

        if created_user_result.error is not None:
            messages.error(request, created_user_result.error.msg)
            self.logger.error(created_user_result.error)
            return render(request, self.template_name, CAPTCHA_CTX)

        if created_user_result.value is None:
            messages.error(request, 'Unexpected error occurred. Please try again.')
            self.logger.error('created user is None')
            return render(request, self.template_name, CAPTCHA_CTX)

        login_result = self.svc.session_manager.login(request, created_user_result.value)
        _redirect = self._redirect

        if login_result.error is not None:
            _redirect = reverse('signin')
            self.logger.error(
                f'User created, but failed to log in automatically: {login_result.error}'
            )

        self.logger.debug(f'redirecting to {_redirect.url}')
        return _redirect


@method_decorator(support.captcha_required('signin'), name='post')
class SignIn(View):
    """View responsável por realizar a autenticação do usuário"""

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template = 'signin.html'
        self.next_url = reverse('rooms')
        self.svc = ClientService(
            repo=ClientRepository(),
            password_manager=DjangoPasswordManager(),
            session_manager=DjangoSessionManager(),
            captcha_service=GoogleRecaptchaV3Verifier(settings.G_RECAPTCHA_KEY_SECRET),
        )

    def get(self, request: HttpRequest, *args, **kwargs):
        next_url = request.GET.get('next', self.next_url)
        request.session['next_url'] = next_url
        request.session.save()
        self.logger.debug(f'next url: {next_url}')

        if request.user.is_authenticated:
            self.logger.info('user already logged in redirected to `rooms`')
            return redirect('rooms')

        self.logger.debug(f'rendering {self.template}')
        return render(request, self.template, CAPTCHA_CTX)

    def post(self, request: HttpRequest, *args, **kwargs):
        post_data = {
            'username': request.POST.get('username'),
            'password': request.POST.get('password'),
        }

        user, err = self.svc.authenticate_user(post_data)
        if err is not None:
            messages.error(request, err.msg)
            self.logger.error(err, exc_info=True)
            return render(request, self.template, CAPTCHA_CTX)

        if user is None:
            messages.error(request, 'Invalid credentials')
            self.logger.error('user is None')
            return render(request, self.template, CAPTCHA_CTX)

        self.svc.session_manager.login(request, user)
        next_url = request.session.get('next_url', self.next_url)
        self.logger.info(f'User logged in successfully. Redirecting to {next_url}')
        return redirect(next_url)


def axes_locked_out(request, *args, **kwargs):
    """callback que add uma msg e redireciona para a url referer
    quando número de tentativas de fazer login é excedia"""
    messages.error(request, 'Número de tentativas excedida. Tente novamente mais tarde.')
    redirect_url = request.META.get('HTTP_REFERER', 'signin')
    return redirect(redirect_url)


def logout_user(request: HttpRequest):
    if request.user.is_authenticated:
        logout(request)
    return redirect('signin')


@method_decorator(profile_ownership_required(), name='dispatch')
class Perfil(LoginRequired, DetailView):
    """view responsável de exibir os dados do usuário"""

    model = Client
    template_name = 'perfil.html'


@method_decorator(support.captcha_required('update_perfil', params=('pk',)), name='post')
@method_decorator(profile_ownership_required(), name='dispatch')
class PerfilUpdate(LoginRequired, UpdateView):
    """view responsável por gerenciar a atualização dos dados do usuário."""

    model = Client
    template_name = 'perfil_update.html'
    form_class = UpdatePerfilForm

    def get_success_url(self) -> str:
        return str(reverse_lazy('perfil', args=(self.object.pk,)))

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **CAPTCHA_CTX}


@method_decorator(
    support.captcha_required('update_perfil_password', params=('pk',)), name='post'
)
@method_decorator(profile_ownership_required(), name='dispatch')
class PerfilChangePassword(LoginRequired, View):
    """view responsável por gerenciar a alteração da senha do usuário"""

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template = 'perfil_update_password.html'
        self.svc = ClientService(
            repo=ClientRepository(),
            password_manager=DjangoPasswordManager(),
            session_manager=DjangoSessionManager(),
            captcha_service=GoogleRecaptchaV3Verifier(settings.G_RECAPTCHA_KEY_SECRET),
        )

    def get(self, *args, **kwargs):
        self.logger.debug(f'rendering {self.template}')
        return render(self.request, self.template, CAPTCHA_CTX)

    def post(self, request, *args, **kwargs):
        _redirect = redirect(reverse('perfil', args=(self.request.user.pk,)))
        data = {
            'user_id': self.request.user.pk,
            'password': self.request.POST.get('new_password', '').strip(),
            'password_repeat': self.request.POST.get('password_repeat', '').strip(),
        }

        inp, err = ChangePasswordInput.safe_validate(data)
        if err is not None:
            self.logger.error(err.msg)
            messages.error(self.request, err.msg)
            return _redirect

        if inp is None:
            self.logger.error('input is None and err is not None')
            messages.error(self.request, 'Dados inválidos')
            return _redirect

        entity, err = self.svc.change_pw(inp)
        if err is not None:
            self.logger.error(err.msg)
            messages.error(self.request, err.msg)
            return _redirect

        if entity is None:
            self.logger.error('input is None and err is not None')
            messages.error(
                self.request,
                'Um error inesperado aconteceu. Por favor tente novamente mais tarde.',
            )
            return _redirect

        messages.success(self.request, PerfilChangePasswordMessages.SUCCESS)
        return _redirect


@method_decorator(support.captcha_required('delete_perfil', params=('pk',)), name='post')
@method_decorator(profile_ownership_required(), name='dispatch')
class PerfilDelete(LoginRequired, DeleteView):
    model = Client
    template_name = 'perfil_delete.html'

    @staticmethod
    def get_success_url() -> str:
        return str(reverse_lazy('rooms'))

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **CAPTCHA_CTX}
