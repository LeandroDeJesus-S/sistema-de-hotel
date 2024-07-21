import logging
from typing import Any
from django.contrib import messages
from django.shortcuts import render, HttpResponse, redirect
from django.db.models import Q
from django.http import HttpRequest
from django.core.exceptions import ValidationError
from django.views import View
from clientes.models import Cliente
from utils.supportviews import SignUpMessages, SignInMessages
from utils.supportmodels import ClienteErrorMessages
from django.contrib.auth import login, authenticate


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

        if not all((username,password,nome,sobrenome, telefone, email, nascimento)):
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
            email=email
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

    def get(self, request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            self.logger.info('usuario ja esta logado. Redirencionando para `quartos`')
            return redirect('quartos')
        
        return render(request, self.template)
    
    def post(self, request: HttpRequest, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, SignInMessages.INVALID_CREDENTIALS)
            return render(request, self.template)
        
        login(request, user)
        msg = SignInMessages.LOGIN_SUCCESS.format_map({'username': user.username})
        messages.success(request, msg)
        return redirect('quartos')
