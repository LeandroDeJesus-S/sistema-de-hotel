import logging
from typing import Any

from dependency_injector.wiring import Provide, inject
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import DeleteView, UpdateView

from clients.application.services import ClientService
from clients.models import Client
from reservations.mixins import LoginRequired
from utils import support

from . import feedback_messages
from .container import ClientsContainer
from .decorators import profile_ownership_required
from .forms import UpdatePerfilForm
from .infra import presenters


@method_decorator(support.captcha_required('signup'), name='post')
class SignUp(View):
    """View responsável por realizar o registro de novos usuários"""

    @inject
    def setup(
        self,
        request: HttpRequest,
        *args: Any,
        svc: ClientService = Provide[ClientsContainer.client_service],
        logger: logging.Logger = Provide[ClientsContainer.logger],
        **kwargs: Any,
    ) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logger
        self.template_name = 'signup.html'
        self._redirect = redirect('rooms')
        self.svc = svc

    def get(self, request):
        if request.user.is_authenticated:
            self.logger.info(f'user already logged in. Redirecting to {self._redirect.url}')
            return self._redirect

        return render(request, self.template_name)

    def post(self, request: HttpRequest):
        result = self.svc.signup_user(request.POST, request)
        return presenters.signup_post_presenter(request, result).unwrap()


@method_decorator(support.captcha_required('signin'), name='post')
class SignIn(View):
    """View responsável por realizar a autenticação do usuário"""

    @inject
    def setup(
        self,
        request: HttpRequest,
        *args: Any,
        svc: ClientService = Provide[ClientsContainer.client_service],
        logger: logging.Logger = Provide[ClientsContainer.logger],
        **kwargs: Any,
    ) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logger
        self.template = 'signin.html'
        self.next_url = reverse('rooms')
        self.svc = svc

    def get(self, request: HttpRequest, *args, **kwargs):
        next_url = request.GET.get('next', self.next_url)
        request.session['next_url'] = next_url
        request.session.save()
        self.logger.debug(f'next url: {next_url}')

        if request.user.is_authenticated:
            self.logger.info('user already logged in redirected to `rooms`')
            return redirect('rooms')

        self.logger.debug(f'rendering {self.template}')
        return render(request, self.template)

    def post(self, request: HttpRequest, *args, **kwargs):
        credentials = {
            'username': request.POST.get('username', ''),
            'password': request.POST.get('password', ''),
        }

        result = self.svc.signin_user(credentials, request)
        redirect_target = result.unwrap() if result.is_ok() else 'error'
        self.logger.info(f'User logged in successfully. Redirecting to {redirect_target}')
        return presenters.signin_post_presenter(request, result).unwrap()


def axes_locked_out(request, *args, **kwargs):
    """callback que add uma msg e redireciona para a url referer
    quando número de tentativas de fazer login é excedia"""
    messages.error(request, feedback_messages.SignIn.LOCKOUT_MESSAGE)
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
        return {**super().get_context_data(**kwargs)}


@method_decorator(
    support.captcha_required('update_perfil_password', params=('pk',)), name='post'
)
@method_decorator(profile_ownership_required(), name='dispatch')
class PerfilChangePassword(LoginRequired, View):
    """view responsável por gerenciar a alteração da senha do usuário"""

    @inject
    def setup(
        self,
        request: HttpRequest,
        *args: Any,
        svc: ClientService = Provide[ClientsContainer.client_service],
        logger: logging.Logger = Provide[ClientsContainer.logger],
        **kwargs: Any,
    ) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logger
        self.template = 'perfil_update_password.html'
        self.svc = svc

    def get(self, *args, **kwargs):
        self.logger.debug(f'rendering {self.template}')
        return render(self.request, self.template)

    def post(self, request, *args, **kwargs):
        result = self.svc.process_password_change(request.POST, self.request.user.pk)

        if result.is_err():
            self.logger.error(result.unwrap_err().msg)

        return presenters.password_change_post_presenter(request, result).unwrap()


@method_decorator(support.captcha_required('delete_perfil', params=('pk',)), name='post')
@method_decorator(profile_ownership_required(), name='dispatch')
class PerfilDelete(LoginRequired, DeleteView):
    model = Client
    template_name = 'perfil_delete.html'

    @staticmethod
    def get_success_url() -> str:
        return str(reverse_lazy('rooms'))

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs)}
