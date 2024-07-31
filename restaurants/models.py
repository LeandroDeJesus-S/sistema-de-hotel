from django.db import models
from home.models import Hotel
from django.core.validators import RegexValidator


class Restaurant(models.Model):
    """restante de um determinado hotel"""
    name = models.CharField(
        'Nome',
        max_length=45,
        unique=True,
        null=False,
        blank=False,
        validators=[
            RegexValidator(r'[\w\s]+')
        ]
    )
    presentation_text = models.TextField(
        'Apresentação',
        max_length=500,
        unique=True,
        null=False,
        blank=False,
    )
    logo = models.ImageField(
        'Logo',
        upload_to='restaurantes/logo',
    )
    hotel = models.OneToOneField(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_restaurants',
        related_query_name='hotel_restaurant'
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Restaurante'
        verbose_name_plural = 'Restaurantes'
