# Generated by Django 3.2.25 on 2024-07-19 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0002_quarto'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quarto',
            name='long_desc',
            field=models.TextField(blank=True, max_length=1000, null=True, verbose_name='Descrição longa'),
        ),
    ]
