# Generated by Django 3.2.25 on 2024-07-29 17:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='Data')),
                ('status', models.CharField(choices=[('F', 'finalizado'), ('C', 'cancelado'), ('P', 'pendente'), ('PR', 'processando')], default='P', max_length=2, verbose_name='Status')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor')),
                ('reservation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment_reservations', related_query_name='payment_reservation', to='reservations.reservation', verbose_name='Reserva')),
            ],
            options={
                'verbose_name': 'Pagamento',
                'verbose_name_plural': 'Pagamentos',
            },
        ),
    ]
