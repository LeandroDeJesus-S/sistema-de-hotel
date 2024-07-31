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
from utils.supportviews import SignUpMessages, SignInMessages
from django.contrib.auth import login, authenticate, logout
from reservations.mixins import LoginRequired
from .forms import UpdatePerfilForm


class SignUp(View):
    """View responsável por realizar o registro de novos usuários"""
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template_name = 'signup.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            self.logger.info('user already logged in. Redirecting to `quartos`')
            return redirect('rooms')
        
        return render(request, self.template_name)
    
    def post(self, request: HttpRequest):
        username = self.request.POST.get('username')
        password = self.request.POST.get('password')
        name = self.request.POST.get('nome')
        surname = self.request.POST.get('sobrenome')
        phone = self.request.POST.get('telefone')
        email = self.request.POST.get('email')
        birthdate = self.request.POST.get('nascimento')
        cpf = self.request.POST.get('cpf')

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
        self.logger.debug('redirecting to `rooms`')
        return redirect('rooms')


class SignIn(View):
    """View responsável por realizar a autenticação do usuário"""
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template = 'signin.html'
        self.next_url = reverse('rooms')

    def get(self, request: HttpRequest, *args, **kwargs):
        next_url = request.GET.get("next", self.next_url)
        self.request.session['next_url'] = next_url
        self.request.session.save()
        self.logger.debug(f'next url: {next_url}')

        if request.user.is_authenticated:
            self.logger.info('user already logged in redirected to `rooms`')
            return redirect('rooms')
        
        self.logger.debug(f'rendering {self.template}')
        return render(request, self.template)
    
    def post(self, request: HttpRequest, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, SignInMessages.INVALID_CREDENTIALS)
            self.logger.error(SignInMessages.INVALID_CREDENTIALS)
            return render(request, self.template)
        
        login(request, user)
        msg = SignInMessages.LOGIN_SUCCESS.format_map({'username': user.username})
        messages.success(request, msg)

        next_url = request.session.get('next_url')
        if next_url:
            del request.session['next_url']
            request.session.save()
        else:
            next_url = self.next_url

        self.logger.info(f'user logged with success. Redirecting to {next_url}')
        return redirect(next_url)


def logout_user(request: HttpRequest):
    if request.user.is_authenticated:
        logout(request)
    return redirect('signin')


def _check_perfil_ownership(request, received_pk):
    """função que verifica se o perfil recebido é o mesmo
    perfil que enviou o request."""
    if request.user.pk != received_pk:
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
    
    def post(self, *args, **kwargs):
        new_pass = self.request.POST.get('new_password')
        pass_repeat = self.request.POST.get('password_repeat')

        if new_pass == pass_repeat:
            self.request.user.set_password(new_pass)
            self.request.user.save()
            messages.success(self.request, 'Senha alterada com sucesso.')
            login(self.request, self.request.user)
            return redirect(reverse('perfil', args=(self.request.user.pk,)))
        
        messages.error(self.request, 'As senhas não são iguais')
        redirect_url = self.request.META.get('HTTP_REFERER', reverse('perfil', args=(self.request.user.pk,)))
        self.logger.info('unmatched passwords')
        return redirect(redirect_url)
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))        
        return super().dispatch(request, *args, **kwargs)


class PerfilDelete(DeleteView):
    model = Client
    template_name = 'perfil_delete.html'

    def get_success_url(self) -> str:
        return reverse_lazy('rooms')
