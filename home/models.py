from django.core.validators import validate_email
from django.db import models
from django.utils.translation import gettext_lazy as gtl

from .rules import ContactRules, HotelRules


class Hotel(models.Model):
    """classe que representa um hotel contendo as informações base
    do site"""

    name = models.CharField(
        'Nome',
        max_length=HotelRules.NAME_MAX_LEN,
        null=False,
        blank=False,
        unique=True,
        help_text=gtl('Nome único do hotel'),
    )
    slogan = models.CharField(
        'Slogan',
        max_length=HotelRules.SLOGAN_MAX_LEN,
        blank=False,
        null=False,
        unique=True,
        help_text=gtl('Frase de destaque exibida no site'),
    )
    logo = models.ImageField(
        'Logo',
        upload_to=HotelRules.LOGO_UPLOAD_PATH,
        help_text=gtl('Imagem do logotipo do hotel (recomendado: PNG transparente)'),
    )
    icon = models.ImageField(
        'Ícone',
        upload_to=HotelRules.ICON_UPLOAD_PATH,
        help_text=gtl('Ícone pequeno do hotel (recomendado: formato quadrado)'),
    )
    presentation_text = models.TextField(
        'Texto de apresentação',
        max_length=HotelRules.PRESENTATION_TEXT_MAX_LEN,
        help_text=gtl(
            'Texto descritivo do hotel exibido na página inicial, até %(max)s caracteres'
        )
        % {'max': HotelRules.PRESENTATION_TEXT_MAX_LEN},
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name_plural = 'Hotéis'


class Contact(models.Model):
    """representa os dados de contato de um hotel"""

    email = models.EmailField(
        'E-mail',
        max_length=ContactRules.EMAIL_MAX_LEN,
        unique=True,
        blank=False,
        null=False,
        validators=[validate_email],
        help_text=gtl('E-mail de contato do hotel (máximo %(max)s caracteres)')
        % {'max': ContactRules.EMAIL_MAX_LEN},
    )
    phone = models.CharField(
        'Telefone',
        max_length=ContactRules.PHONE_MAX_LEN,
        null=False,
        blank=False,
        unique=True,
        help_text=gtl('Telefone fixo do hotel'),
    )
    whatsapp = models.CharField(
        'Whatsapp',
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        null=False,
        blank=False,
        unique=True,
        help_text=gtl('Número do WhatsApp para atendimento (máximo %(max)s caracteres)')
        % {'max': ContactRules.SOCIAL_MEDIA_MAX_LEN},
    )
    instagram = models.CharField(
        'Instagram',
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        help_text=gtl('Nome de usuário do Instagram (sem @, máximo %(max)s caracteres)')
        % {'max': ContactRules.SOCIAL_MEDIA_MAX_LEN},
    )
    facebook = models.CharField(
        'Facebook',
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        help_text=gtl('URL ou nome da página no Facebook'),
    )
    twitter = models.CharField(
        'Twitter',
        max_length=ContactRules.SOCIAL_MEDIA_MAX_LEN,
        help_text=gtl('Nome de usuário do Twitter (sem @, máximo %(max)s caracteres)')
        % {'max': ContactRules.SOCIAL_MEDIA_MAX_LEN},
    )
    hotel = models.OneToOneField(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_contacts',
        related_query_name='hotel_contact',
        verbose_name='Hotel',
        help_text=gtl('Hotel ao qual estes contatos pertencem'),
    )

    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.pk}'

    class Meta:
        verbose_name = 'Contato'
        verbose_name_plural = 'Contatos'
