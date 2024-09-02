# Generated by Django 3.2.25 on 2024-08-17 03:31

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_auto_20240729_1906'),
    ]

    operations = [
        migrations.AlterField(
            model_name='class',
            name='name',
            field=models.CharField(max_length=15, unique=True, validators=[django.core.validators.RegexValidator('^\\w[\\w ]*$', 'Nome da classe é inválido.')], verbose_name='Classe'),
        ),
    ]
