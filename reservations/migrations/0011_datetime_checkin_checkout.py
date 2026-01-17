# Generated manually for datetime migration

from django.db import migrations, models
from datetime import timedelta


def migrate_checkin_checkout_forward(apps, schema_editor):
    """Convert existing date fields to datetime: checkin=14:00, checkout=12:00 next day"""
    Reservation = apps.get_model('reservations', 'Reservation')

    for reservation in Reservation.objects.all():
        # Convert date to datetime: checkin at 14:00, checkout at 12:00 next day
        reservation.checkin = reservation.checkin.replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        reservation.checkout = (reservation.checkout + timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        reservation.save()


def migrate_checkin_checkout_reverse(apps, schema_editor):
    """Reverse migration: convert back to dates"""
    Reservation = apps.get_model('reservations', 'Reservation')

    for reservation in Reservation.objects.all():
        # Convert datetime back to date
        reservation.checkin = reservation.checkin.date()
        reservation.checkout = reservation.checkout.date()
        reservation.save()


class Migration(migrations.Migration):
    dependencies = [
        ('reservations', '0010_auto_20251222_2117'),
    ]

    operations = [
        # First, convert DateField to DateTimeField
        migrations.AlterField(
            model_name='reservation',
            name='checkin',
            field=models.DateTimeField(
                blank=False,
                null=False,
                help_text='Check-in date and time in YYYY-MM-DD HH:MM:SS format',
                verbose_name='Check-in',
            ),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='checkout',
            field=models.DateTimeField(
                blank=False,
                null=False,
                help_text='Check-out date and time in YYYY-MM-DD HH:MM:SS format',
                verbose_name='Check-out',
            ),
        ),
        # RunPython to convert existing data
        migrations.RunPython(
            migrate_checkin_checkout_forward,
            migrate_checkin_checkout_reverse,
        ),
    ]
