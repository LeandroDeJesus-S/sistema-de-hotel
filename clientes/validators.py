import re
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


def validate_phone_number(phone):
    re_match = re.match(r"^[1-9]\d{0,1}9\d{7,8}$", phone)
    if re_match is None:
        raise ValidationError(f'Número de telefone inválido: {phone}')


@deconstructible
class ValidateFieldLength:
    def __init__(self, fieldname, min_, max_) -> None:
        self.fieldname = fieldname
        self.min = min_
        self.max = max_

    def __call__(self, field):
        regex = '^\w{%d,%d}$' % (self.min, self.max)
        if not re.match(regex, field):
            raise ValidationError({
                self.fieldname.lower(): f'{self.fieldname} precisa ter de {self.min} a {self.max} caracteres'
            })
    
    def __eq__(self, value) -> bool:
        return self.fieldname == value.fieldname
