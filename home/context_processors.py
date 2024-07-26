from .models import Hotel, Contact


def hotel(*args, **kwargs):
    _hotel = Hotel.objects.first()
    contact = Contact.objects.filter(hotel=_hotel).first()
    return {'hotel': _hotel, 'hotel_contact': contact}
