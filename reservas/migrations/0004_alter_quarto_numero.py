# Generated by Django 3.2.25 on 2024-07-25 23:37

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0003_beneficio_displayable_on_homepage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quarto',
            name='numero',
            field=models.CharField(max_length=4, unique=True, validators=[django.core.validators.RegexValidator('^\\d{3}[A-Z]?$')], verbose_name='Número'),
        ),
    ]
