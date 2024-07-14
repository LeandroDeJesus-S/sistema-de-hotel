# Generated by Django 3.2.25 on 2024-07-14 00:15

import clientes.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=25, validators=[clientes.validators.ValidateFieldLength('Primeiro nome', 2, 25), django.core.validators.RegexValidator('[A-Za-z]{2,25}', 'O nome deve conter apenas letras')], verbose_name='Nome')),
                ('sobrenome', models.CharField(max_length=50, validators=[clientes.validators.ValidateFieldLength('Sobrenome', 2, 50), django.core.validators.RegexValidator('[A-Za-z]{2,50}', 'O nome deve conter apenas letras')], verbose_name='Sobrenome')),
                ('nascimento', models.DateField(blank=True, null=True, verbose_name='Data de nascimento')),
            ],
        ),
        migrations.CreateModel(
            name='Contato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=255, unique=True, validators=[django.core.validators.EmailValidator()], verbose_name='E-mail')),
                ('telefone', models.CharField(max_length=11, validators=[clientes.validators.validate_phone_number], verbose_name='Telefone')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contatos', related_query_name='contato', to='clientes.cliente')),
            ],
        ),
        migrations.AddConstraint(
            model_name='cliente',
            constraint=models.UniqueConstraint(fields=('nome', 'sobrenome', 'nascimento'), name='unique_client'),
        ),
    ]
