import logging
from typing import Any
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, HttpResponse, redirect
from django.urls import reverse, reverse_lazy
from django.http import HttpRequest
from django.core.exceptions import ValidationError
from django.views import View
from django.views.generic.edit import UpdateView, DeleteView
from django.views.generic.detail import DetailView
from clients.models import Client
from utils import support
from utils.supportviews import SignUpMessages, SignInMessages, PerfilChangePasswordMessages
from django.contrib.auth import login, authenticate, logout
from reservations.mixins import LoginRequired
from .forms import UpdatePerfilForm


class SignUp(View):
    """View responsável por realizar o registro de novos usuários"""
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template_name = 'signup.html'
        self._redirect = redirect('rooms')
    
    def get(self, request):
        if request.user.is_authenticated:
            self.logger.info(f'user already logged in. Redirecting to {self._redirect.url}')
            return self._redirect
        
        return render(request, self.template_name)
    
    def post(self, request: HttpRequest):
        username = self.request.POST.get('username', '').strip()
        password = self.request.POST.get('password')
        name = self.request.POST.get('nome', '').strip()
        surname = self.request.POST.get('sobrenome', '').strip()
        phone = self.request.POST.get('telefone', '').strip()
        email = self.request.POST.get('email', '').strip()
        birthdate = self.request.POST.get('nascimento')
        cpf = self.request.POST.get('cpf', '').strip()
        captcha = request.POST.get('g-recaptcha-response')
        if not support.verify_captcha(captcha):
            self.logger.debug(f'captcha response: {captcha}')
            messages.error(request, 'Mr. Robot, é você???')
            return redirect(request.META.get('HTTP_REFERER', 'signup'))

        if not all((username,password,name,surname, phone, email, birthdate, cpf)):
            messages.error(request, SignUpMessages.MISSING)
            self.logger.error('missing fields')
            return render(request, self.template_name)
        
        client = Client(
            username=username,
            password=password,
            first_name=name,
            last_name=surname,
            phone=phone,
            birthdate=birthdate,
            email=email,
            cpf=cpf,
        )

        try:
            client.full_clean()
        except ValidationError as e:
            messages.error(request, e.messages[0])
            self.logger.error(str(e.error_dict))
            return render(request, self.template_name)
        
        client.set_password(client.password)
        client.save()

        login(request, client)
        _redirect = self._redirect
        self.logger.debug(f'redirecting to {_redirect.url}')
        return _redirect


class SignIn(View):
    """View responsável por realizar a autenticação do usuário"""
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template = 'signin.html'
        self.next_url = reverse('rooms')

    def get(self, request: HttpRequest, *args, **kwargs):
        next_url = request.GET.get("next", self.next_url)
        request.session['next_url'] = next_url
        request.session.save()
        self.logger.debug(f'next url: {next_url}')

        if request.user.is_authenticated:
            self.logger.info('user already logged in redirected to `rooms`')
            return redirect('rooms')
        
        self.logger.debug(f'rendering {self.template}')
        return render(request, self.template)
    
    def post(self, request: HttpRequest, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        captcha = request.POST.get('g-recaptcha-response')
        if not support.verify_captcha(captcha):
            self.logger.debug(f'captcha response: {captcha}')
            messages.error(request, 'Mr. Robot, é você???')
            return redirect(request.META.get('HTTP_REFERER', 'signin'))

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, SignInMessages.INVALID_CREDENTIALS)
            self.logger.error(SignInMessages.INVALID_CREDENTIALS)
            return render(request, self.template)
        
        login(request, user)

        next_url = request.session.get('next_url')
        self.logger.info(f'next url in the session: {next_url}')
        if next_url:
            deleted = request.session.pop('next_url')
            request.session.save()
            self.logger.debug(f'delete {deleted} from session')
        else:
            next_url = self.next_url

        self.logger.info(f'user logged with success. Redirecting to {next_url}')
        return redirect(next_url)


def axes_locked_out(request, *args, **kwargs):
    """callback que add uma msg e redireciona para a url referer
    quando número de tentativas de fazer login é excedia"""
    messages.error(
        request,
        'Número de tentativas excedida. Tente novamente mais tarde.'
    )
    redirect_url = request.META.get('HTTP_REFERER', 'signin')
    return redirect(redirect_url)


def logout_user(request: HttpRequest):
    if request.user.is_authenticated:
        logout(request)
    return redirect('signin')


def _check_perfil_ownership(request, received_pk):
    """função que verifica se o perfil recebido é o mesmo
    perfil que enviou o request."""
    if request.user.is_authenticated and request.user.pk != received_pk:
        logging.getLogger('djangoLogger').warn(f'{request.user.pk} != {received_pk}')
        raise PermissionDenied
    

class Perfil(LoginRequired, DetailView):
    """view responsável de exibir os dados do usuário"""
    model = Client
    template_name = 'perfil.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)


class PerfilUpdate(LoginRequired, UpdateView):
    """view responsável por gerenciar a atualização dos dados do usuário."""
    model = Client
    template_name = 'perfil_update.html'
    form_class = UpdatePerfilForm

    def get_success_url(self) -> str:
        return reverse_lazy('perfil', args=(self.object.pk,))
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)


class PerfilChangePassword(LoginRequired, View):
    """view responsável por gerenciar a alteração da senha do usuário"""
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template = 'perfil_update_password.html'
    
    def get(self, *args, **kwargs):
        self.logger.debug(f'rendering {self.template}')    
        return render(self.request, self.template)
    
    def post(self, request, *args, **kwargs):
        new_pass = self.request.POST.get('new_password')
        pass_repeat = self.request.POST.get('password_repeat')
        captcha = request.POST.get('g-recaptcha-response')
        if not support.verify_captcha(captcha):
            messages.error(request, 'Mr. Robot, é você???')
            default_url = reverse('update_perfil_password', args=(request.user.pk,))
            return redirect(request.META.get('HTTP_REFERER', default_url))

        if new_pass == pass_repeat:
            self.request.user.set_password(new_pass)
            self.request.user.save()
            messages.success(self.request, PerfilChangePasswordMessages.SUCCESS)
            login(self.request, self.request.user)
            return redirect(reverse('perfil', args=(self.request.user.pk,)))
        
        messages.error(self.request, PerfilChangePasswordMessages.PASSWORDS_DIFFERS)
        redirect_url = self.request.META.get('HTTP_REFERER', reverse('perfil', args=(self.request.user.pk,)))
        self.logger.info('unmatched passwords')
        return redirect(redirect_url)
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))        
        return super().dispatch(request, *args, **kwargs)


class PerfilDelete(LoginRequired, DeleteView):
    model = Client
    template_name = 'perfil_delete.html'

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        captcha = request.POST.get('g-recaptcha-response')
        if not support.verify_captcha(captcha):
            messages.error(request, 'Mr. Robot, é você???')
            return redirect(request.META.get('HTTP_REFERER', 'delete_perfil'))
        
        return super().post(request, *args, **kwargs)

    def get_success_url(self) -> str:
        return reverse_lazy('rooms')
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))        
        return super().dispatch(request, *args, **kwargs)
