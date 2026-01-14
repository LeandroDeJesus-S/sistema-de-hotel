from django.core.validators import validate_email
from django.db import models
from django.utils.translation import gettext_lazy as gtl

from .rules import ContactRules, HotelRules


class Hotel(models.Model):
    """Class that represents a hotel containing basic website information"""

    name = models.CharField(
        gtl('Name'),
        max_length=HotelRules.NAME_MAX_LEN,
        null=False,
        blank=False,
        unique=True,
        help_text=gtl('Unique name of the hotel'),
    )
    slogan = models.CharField(
        gtl('Slogan'),
        max_length=HotelRules.SLOGAN_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        help_text=gtl('Tagline displayed on the website'),
    )
    logo = models.ImageField(
        gtl('Logo'),
        upload_to=HotelRules.LOGO_UPLOAD_PATH,
        help_text=gtl('Hotel logo image (recommended: transparent PNG)'),
    )
    icon = models.ImageField(
        gtl('Icon'),
        upload_to=HotelRules.ICON_UPLOAD_PATH,
        help_text=gtl('Small hotel icon (recommended: square format)'),
    )
    presentation_text = models.TextField(
        gtl('Presentation text'),
        max_length=HotelRules.PRESENTATION_TEXT_MAX_LEN,
        help_text=gtl(
            'Hotel description text displayed on the homepage, up to %(max)s characters'
        )
        % {'max': HotelRules.PRESENTATION_TEXT_MAX_LEN},
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name_plural = 'Hotels'


class Contact(models.Model):
    """Represents the contact details of a hotel"""

    email = models.EmailField(
        gtl('Email'),
        max_length=ContactRules.EMAIL_MAX_LEN,
        unique=True,
        blank=False,
        null=False,
        validators=[validate_email],
        help_text=gtl('Hotel contact email (maximum %(max)s characters)')
        % {'max': ContactRules.EMAIL_MAX_LEN},
    )
    phone = models.CharField(
        gtl('Phone'),
        max_length=ContactRules.PHONE_MAX_LEN,
        null=False,
        blank=False,
        unique=True,
        help_text=gtl('Hotel landline phone'),
    )
    whatsapp = models.CharField(
        gtl('Whatsapp'),
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        null=False,
        blank=False,
        unique=True,
        help_text=gtl('WhatsApp number for customer service (maximum %(max)s characters)')
        % {'max': ContactRules.SOCIAL_MEDIA_MAX_LEN},
    )
    instagram = models.CharField(
        gtl('Instagram'),
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        help_text=gtl('Instagram username (without @, maximum %(max)s characters)')
        % {'max': ContactRules.SOCIAL_MEDIA_MAX_LEN},
    )
    facebook = models.CharField(
        gtl('Facebook'),
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        help_text=gtl('Facebook page URL or name'),
    )
    twitter = models.CharField(
        gtl('Twitter'),
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        help_text=gtl('Twitter username (without @, maximum %(max)s characters)')
        % {'max': ContactRules.SOCIAL_MEDIA_MAX_LEN},
    )
    hotel = models.OneToOneField(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_contacts',
        related_query_name='hotel_contact',
        verbose_name='Hotel',
        help_text=gtl('Hotel to which these contacts belong'),
    )

    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.pk}'

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
