from typing import Iterable
from django.db import models
from home.models import Hotel
from django.core.validators import RegexValidator
from utils import support
from utils.supportmodels import ServicesRules


class Service(models.Model):
    """serviços de um determinado hotel"""
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
        upload_to='services/logo',
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_services',
        related_query_name='hotel_service'
    )

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        if self.logo:
            support.resize_image(self.logo.path, *ServicesRules.IMG_SIZE)

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'
