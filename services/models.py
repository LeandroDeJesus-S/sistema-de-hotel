from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as gtl

from home.models import Hotel
from services.rules import ServiceRules
from utils.adapters.image_validators import validate_service_logo
from utils.models.middleware import ResizeImageMiddleware, model_middleware


@model_middleware(
    ResizeImageMiddleware(
        field_name='logo',
        w=ServiceRules.IMG_SIZE[0],
        h=ServiceRules.IMG_SIZE[1],
        create_only=False,
    )
)
class Service(models.Model):
    """Hotel services"""

    name = models.CharField(
        gtl('Name'),
        max_length=ServiceRules.NAME_MAX_LEN,
        unique=True,
        null=False,
        blank=False,
        validators=[RegexValidator(r'[\w\s]+')],
        help_text=gtl(
            'Unique name of the service offered by the hotel (maximum %(max)s characters)'
        )
        % {'max': ServiceRules.NAME_MAX_LEN},
    )
    presentation_text = models.TextField(
        gtl('Presentation'),
        max_length=ServiceRules.PRESENTATION_TEXT_MAX_LEN,
        unique=True,
        null=False,
        blank=False,
        help_text=gtl('Descriptive text of the service (up to %(max)s characters)')
        % {'max': ServiceRules.PRESENTATION_TEXT_MAX_LEN},
    )
    logo = models.ImageField(
        gtl('Logo'),
        upload_to=ServiceRules.LOGO_UPLOAD_PATH,
        validators=[validate_service_logo],
        help_text=gtl('Service logo image or icon'),
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_services',
        related_query_name='hotel_service',
        help_text=gtl('Hotel to which the service belongs'),
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
