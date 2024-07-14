import re

from datetime import datetime
from django.core.exceptions import ValidationError


def validate_model(model, **kwargs):
    try:
        model.full_clean(**kwargs)
    except ValidationError as error:
        return error.messages.pop(0)

