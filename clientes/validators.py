import re
from django.core.exceptions import ValidationError


def validate_phone_number(phone):
    re_match = re.match(r"^[1-9]\d{0,1}9\d{7,8}$", phone)
    if re_match is None:
        raise ValidationError(f'Numero de telefone inválido: {phone}')
