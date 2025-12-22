from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from home.models import Hotel
from services.rules import ServicesRules
from utils.adapters.image_validators import MaxSizeImageValidator, django_image_validator
from utils.models.middleware import ResizeImageMiddleware, model_middleware


@model_middleware(
    ResizeImageMiddleware(
        field_name='logo',
        w=ServicesRules.IMG_SIZE[0],
        h=ServicesRules.IMG_SIZE[1],
        create_only=False,
    )
)
class Service(models.Model):
    """serviços de um determinado hotel"""

    name = models.CharField(
        'Nome',
        max_length=45,
        unique=True,
        null=False,
        blank=False,
        validators=[RegexValidator(r'[\w\s]+')],
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
        validators=[
            django_image_validator(
                MaxSizeImageValidator(
                    max_size=5, raise_exception=True, exception_class=ValidationError
                )
            )
        ],
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_services',
        related_query_name='hotel_service',
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'
