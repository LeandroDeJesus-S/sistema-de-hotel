from django.db import models
from django.core.validators import validate_email


class Hotel(models.Model):
    name = models.CharField(
        'Nome',
        max_length=45,
        null=False,
        blank=False,
        unique=True
    )
    slogan = models.CharField(
        'Slogan',
        max_length=100,
        blank=False,
        null=False,
        unique=True
    )
    logo = models.ImageField(
        'Logo',
        upload_to='hotel/logo',
    )
    icon = models.ImageField(
        'Ícone',
        upload_to='hotel/icon',
    )
    presentation_text = models.TextField(
        'Texto de apresentação',
        max_length=1000,
    )

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        verbose_name_plural = 'Hotéis'


class Contact(models.Model):
    email = models.EmailField(
        'E-mail',
        max_length=155,
        unique=True,
        blank=False,
        null=False,
        validators=[
            validate_email
        ]
    )
    phone = models.CharField(
        'Telefone', 
        max_length=11,
        null=False,
        blank=False,
        unique=True
    )
    whatsapp = models.CharField(
        'Whatsapp', 
        max_length=255,
        null=False,
        blank=False,
        unique=True
    )
    instagram = models.CharField(
        'Instagram',
        max_length=255,
    )
    facebook = models.CharField(
        'Facebook',
        max_length=255
    )
    twitter = models.CharField(
        'Twitter',
        max_length=255,
    )
    hotel = models.OneToOneField(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_contacts',
        related_query_name='hotel_contact',
        verbose_name='Hotel'
    )

    def __str__(self) -> str:
        return f'<{self.__class__.__name__}: {self.pk}>'

    class Meta:
        verbose_name = 'Contato'
        verbose_name_plural = 'Contatos'
