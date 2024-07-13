from datetime import datetime
from django.core.exceptions import ValidationError


def validate_model(model):
    try:
        model.full_clean()
    except ValidationError as error:
        return error.messages

