# Generated by Django 4.2.2 on 2023-06-16 00:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0004_alter_reserva_check_in_alter_reserva_checkout'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reserva',
            name='telefone',
            field=models.CharField(max_length=15, verbose_name='Telefone'),
        ),
    ]
