from django.conf import settings
from dotenv import load_dotenv

from .models import ContactChannel, Hotel


def hotel(*args, **kwargs):
    _hotel = Hotel.objects.first()
    contact_channels = ContactChannel.objects.filter(hotel=_hotel, active=True)
    return {'hotel': _hotel, 'contact_channels': contact_channels}


def recaptcha(*args, **kwargs):
    load_dotenv()
    return {'recaptcha_site_key': settings.G_RECAPTCHA_KEY_SITE}
