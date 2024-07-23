import re
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from utils.supportmodels import ContatoErrorMessages


def validate_phone_number(phone):
    re_match = re.match(r"^[1-9]\d{0,1}9\d{7,8}$", phone)
    if re_match is None:
        raise ValidationError(ContatoErrorMessages.INVALID_PHONE)
