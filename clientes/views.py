import logging
from typing import Any
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, HttpResponse, redirect
from django.urls import reverse, reverse_lazy
from django.db.models import Q
from django.http import HttpRequest
from django.core.exceptions import ValidationError
from django.views import View
from django.views.generic.edit import UpdateView
from django.views.generic.detail import DetailView
from clientes.models import Cliente
from utils.supportviews import SignUpMessages, SignInMessages
from utils.supportmodels import ClienteErrorMessages
from django.contrib.auth import login, authenticate, logout
from reservas.mixins import LoginRequired
from django_q.tasks import async_task, Task
from secrets import token_hex
from datetime import datetime, timedelta


class SignUp(View):
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template_name = 'signup.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            self.logger.info('usuario ja esta logado. Redirencionando para `quartos`')
            return redirect('quartos')
        
        return render(request, self.template_name)
    
    def post(self, request: HttpRequest):
        username = self.request.POST.get('username')
        password = self.request.POST.get('password')
        nome = self.request.POST.get('nome')
        sobrenome = self.request.POST.get('sobrenome')
        telefone = self.request.POST.get('telefone')
        email = self.request.POST.get('email')
        nascimento = self.request.POST.get('nascimento')
        cpf = self.request.POST.get('cpf')

        if not all((username,password,nome,sobrenome, telefone, email, nascimento, cpf)):
            messages.error(request, SignUpMessages.MISSING)
            self.logger.error(SignUpMessages.MISSING)
            return render(request, self.template_name)
        
        client = Cliente(
            username=username,
            password=password,
            nome=nome,
            sobrenome=sobrenome,
            telefone=telefone,
            nascimento=nascimento,
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
        self.logger.debug('redirecionado para `quartos`')
        return redirect('quartos')


class SignIn(View):
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.template = 'signin.html'
        self.next_url = reverse('quartos')

    def get(self, request: HttpRequest, *args, **kwargs):
        next_url = request.GET.get("next", self.next_url)
        self.request.session['next_url'] = next_url
        self.request.session.save()
        self.logger.debug(f'next url: {next_url}')

        if request.user.is_authenticated:
            self.logger.info('usuario ja esta logado. Redirencionando para `quartos`')
            return redirect('quartos')
        
        self.logger.debug('renderizando pagina de login')
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
        next_url = next_url if next_url is not None else self.next_url

        self.logger.info(f'usuario logado com sucesso. Redirecionando para {next_url}')
        return redirect(next_url)


def logout_user(request: HttpRequest):
    if request.user.is_authenticated:
        logout(request)
    return redirect('signin')


def _check_perfil_ownership(request, received_pk):
    if request.user.pk != received_pk:
        raise PermissionDenied
    

class Perfil(LoginRequired, DetailView):
    model = Cliente
    template_name = 'perfil.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)


class PerfilUpdate(LoginRequired, UpdateView):
    model = Cliente
    fields = (
        'username',
        'nome',
        'sobrenome',
        'nascimento'
    )
    template_name = 'perfil_update.html'

    def get_success_url(self) -> str:
        return reverse_lazy('perfil', args=(self.object.pk,))
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)


class PerfilChangePassword(LoginRequired, View):   
    def get(self, *args, **kwargs):        
        return render(self.request, 'perfil_update_password.html')
    
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
        return redirect(redirect_url)
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        _check_perfil_ownership(request, kwargs.get('pk'))        
        return super().dispatch(request, *args, **kwargs)
    
