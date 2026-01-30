from clients.domain.value_objects import Language
from reservations.domain.value_objects import Currency


def get_default_currency(language: Language) -> Currency:
    """Infer currency from user language enum."""
    return {
        Language.EN: Currency.USD,
        Language.PT_BR: Currency.BRL,
    }.get(language, Currency.USD)


def get_currency_for_language_code(lang_code: str) -> Currency:
    """
    Returns the preferred currency for a language code string, defaults to USD.
    Tries to map the string to a Language enum first.
    """
    if not lang_code:
        return Currency.USD

    # Normalize: Django might give 'en-us', 'pt-br', 'pt'.
    lang_lower = lang_code.lower()

    # Try exact match
    try:
        language_enum = Language(lang_lower)
        return get_default_currency(language_enum)
    except ValueError:
        pass

    # Try matching prefix if exact match fails
    if lang_lower.startswith('pt'):
        return get_default_currency(Language.PT_BR)
    elif lang_lower.startswith('en'):
        return get_default_currency(Language.EN)

    return Currency.USD


def get_currency_symbol(currency: Currency) -> str:
    """Returns the symbol string for the Currency Enum."""
    return {
        Currency.BRL: 'R$',
        Currency.USD: '$',
    }.get(currency, '$')
