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
    """serviços de um determinado hotel"""

    name = models.CharField(
        'Nome',
        max_length=ServiceRules.NAME_MAX_LEN,
        unique=True,
        null=False,
        blank=False,
        validators=[RegexValidator(r'[\w\s]+')],
        help_text=gtl('Nome único do serviço oferecido pelo hotel (máximo %(max)s caracteres)')
        % {'max': ServiceRules.NAME_MAX_LEN},
    )
    presentation_text = models.TextField(
        'Apresentação',
        max_length=ServiceRules.PRESENTATION_TEXT_MAX_LEN,
        unique=True,
        null=False,
        blank=False,
        help_text=gtl('Texto descritivo do serviço (até %(max)s caracteres)')
        % {'max': ServiceRules.PRESENTATION_TEXT_MAX_LEN},
    )
    logo = models.ImageField(
        'Logo',
        upload_to=ServiceRules.LOGO_UPLOAD_PATH,
        validators=[validate_service_logo],
        help_text=gtl('Imagem do logotipo ou ícone do serviço'),
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='hotel_services',
        related_query_name='hotel_service',
        help_text=gtl('Hotel ao qual o serviço pertence'),
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'
