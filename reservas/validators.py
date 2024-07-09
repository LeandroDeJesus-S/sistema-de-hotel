from datetime import datetime
from django.core.exceptions import ValidationError


def validate_model(model):
    try:
        model.validate_constraints()
        model.validate_unique()
    except ValidationError as error:
        return error.messages
