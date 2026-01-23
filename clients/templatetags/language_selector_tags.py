from django.template import Library
from django.utils.translation import get_language

register = Library()


@register.inclusion_tag('clients/templatetags/language_selector.html')
def language_selector():
    """Inclusion tag for language selector component"""
    current_language = get_language() or 'en'

    languages = [
        {
            'code': 'en',
            'name': 'English',
            'flag_class': 'fas fa-flag-usa',
        },
        {
            'code': 'pt-br',
            'name': 'Portuguese',
            'flag_class': 'fas fa-flag',
        },
    ]

    return {
        'current_language': current_language,
        'languages': languages,
    }
