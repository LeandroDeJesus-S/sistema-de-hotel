from django.db import models
from django.utils.translation import gettext_lazy as gtl

from .rules import HotelRules


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


class ContactChannel(models.Model):
    """Represents a contact channel for a hotel (email, phone, social media, etc.)"""

    name = models.CharField(
        gtl('Name'),
        max_length=45,
        unique=True,
        null=False,
        blank=False,
        help_text=gtl('Short identifier name for the contact channel'),
    )
    display_name = models.CharField(
        gtl('Display name'),
        max_length=45,
        unique=True,
        null=False,
        blank=False,
        help_text=gtl('Name displayed to users'),
    )
    html_icon = models.CharField(
        gtl('HTML icon'),
        max_length=20,
        null=True,
        blank=True,
        help_text=gtl('HTML class name for the icon (e.g., fa-whatsapp)'),
    )
    value = models.TextField(
        gtl('Value'),
        null=True,
        blank=True,
        help_text=gtl('The actual URL or contact value'),
    )
    display_value = models.CharField(
        gtl('Display value'),
        max_length=45,
        unique=True,
        null=False,
        blank=False,
        help_text=gtl('User-friendly display value (e.g., phone number, @username)'),
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='contact_channels',
        verbose_name=gtl('Hotel'),
        help_text=gtl('Hotel to which this contact channel belongs'),
    )
    active = models.BooleanField(
        gtl('Active'),
        default=False,
        help_text=gtl('Whether this contact channel is available and displayed'),
    )

    def __str__(self) -> str:
        return f'{self.display_name} ({self.hotel.name})'

    class Meta:
        verbose_name = gtl('Contact channel')
        verbose_name_plural = gtl('Contact channels')
