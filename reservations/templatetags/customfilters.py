from django.template import Library

register = Library()


@register.filter
def pluralized_capacity(capacity):
    result = 'pessoas' if int(capacity) > 1 else 'pessoa'
    return f'{capacity} {result}'

