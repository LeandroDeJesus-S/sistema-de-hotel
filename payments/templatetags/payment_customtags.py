from decimal import Decimal
from django.template import Library

register = Library()


@register.filter
def money(value):
    if isinstance(value, float|Decimal):
        return f'R${value:.2f}'
    
    elif isinstance(value, str):
        try:
            value = value.replace(',', '.')
            float_value = float(value)
            return f'R${float_value:.2f}'
        except ValueError as exc:
            raise exc
    
    raise TypeError(f'value must be an instance of float, Decimal or str but have {value.__class__}')
