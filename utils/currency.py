from clients.domain.entities import Language
from reservations.domain.value_objects import Currency


def get_default_currency(language: Language) -> Currency:
    """Infer currency from user language."""
    return {
        Language.EN: Currency.USD,
        Language.PT_BR: Currency.BRL,
    }.get(language, Currency.USD)
