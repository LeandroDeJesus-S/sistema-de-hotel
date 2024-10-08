# Generated by Django 3.2.25 on 2024-07-29 17:28

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Hotel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=45, unique=True, verbose_name='Nome')),
                ('slogan', models.CharField(max_length=100, unique=True, verbose_name='Slogan')),
                ('logo', models.ImageField(upload_to='hotel/logo', verbose_name='Logo')),
                ('icon', models.ImageField(upload_to='hotel/icon', verbose_name='Ícone')),
                ('presentation_text', models.TextField(max_length=1000, verbose_name='Texto de apresentação')),
            ],
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=155, unique=True, validators=[django.core.validators.EmailValidator()], verbose_name='E-mail')),
                ('phone', models.CharField(max_length=11, unique=True, verbose_name='Telefone')),
                ('whatsapp', models.CharField(max_length=255, unique=True, verbose_name='Whatsapp')),
                ('instagram', models.CharField(max_length=255, verbose_name='Instagram')),
                ('facebook', models.CharField(max_length=255, verbose_name='Facebook')),
                ('twitter', models.CharField(max_length=255, verbose_name='Twitter')),
                ('hotel', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='hotel_contacts', related_query_name='hotel_contact', to='home.hotel', verbose_name='Hotel')),
            ],
        ),
    ]
