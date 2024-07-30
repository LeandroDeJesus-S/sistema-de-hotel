from datetime import datetime
from django.core.exceptions import ValidationError


def validate_model(model, **kwargs):
    try:
        model.full_clean(**kwargs)
    except ValidationError as error:
        return error.messages.pop(0)


def convert_date(value: str):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return datetime(1,1,1).date()
