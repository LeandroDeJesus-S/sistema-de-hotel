import re
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from utils.supportmodels import ContatoErrorMessages


def validate_phone_number(phone):
    re_match = re.match(r"^[1-9]\d{0,1}9\d{7,8}$", phone)
    if re_match is None:
        raise ValidationError(ContatoErrorMessages.INVALID_PHONE)


@deconstructible
class ValidateFieldLength:
    def __init__(self, fieldname, min_, max_) -> None:
        self.fieldname = fieldname
        self.min = min_
        self.max = max_

    def __call__(self, field):
        regex = '^\w{%d,%d}$' % (self.min, self.max)
        if not re.match(regex, field):
            raise ValidationError(f'{self.fieldname} precisa ter de {self.min} a {self.max} caracteres')
    
    def __eq__(self, other) -> bool:
        return (
            isinstance(other, ValidateFieldLength) and
            self.fieldname == other.fieldname and
            self.min == other.min and
            self.max == other.max
        )
