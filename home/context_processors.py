from .models import Hotel, Contact
from django.conf import settings
from dotenv import load_dotenv


def hotel(*args, **kwargs):
    _hotel = Hotel.objects.first()
    contact = Contact.objects.filter(hotel=_hotel).first()
    return {'hotel': _hotel, 'hotel_contact': contact}


def recaptcha(*args, **kwargs):
    load_dotenv()
    return {'recaptcha_site_key': settings.G_RECAPTCHA_KEY_SITE}
