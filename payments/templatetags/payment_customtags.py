from decimal import Decimal
from django.template import Library

register = Library()


@register.filter
def money(value):
    if isinstance(value, float|Decimal):
        return f'R${value:.2f}'
    
    elif isinstance(value, str) and value.isnumeric():
        try:
            float_value = float(value)
            return f'R${float_value}'
        except TypeError as e:
            e.__annotations__['note'] = 'Erro ao converter a string para float'
            raise e
    
    raise TypeError
