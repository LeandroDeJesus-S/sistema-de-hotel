from django import template
from django.db.models import Manager
from django.utils.translation import get_language

from utils.currency import get_currency_for_language_code, get_currency_symbol

register = template.Library()


@register.simple_tag()
def lang_to_currency(language_code):
    return get_currency_for_language_code(language_code)


@register.inclusion_tag('reservations/templatetags/currency_selector.html')
def currency_selector(room_prices):
    """Inclusion tag for currency selector dropdown.

    Selects the currency matching user's current language if available,
    otherwise selects the first active currency.

    Args:
        room_prices: List of price objects with currency and active attributes.

    Returns:
        dict: Context for the template with processed prices list.
    """
    current_lang = get_language()
    lang_currency = get_currency_for_language_code(current_lang)

    prices = []
    selected_set = False

    # Handle Django ManyRelatedManager
    if isinstance(room_prices, Manager) or hasattr(room_prices, 'all'):
        room_prices = room_prices.all()

    for price in room_prices:
        if price.active:
            is_selected = False
            if not selected_set and price.currency == lang_currency:
                is_selected = True
                selected_set = True

            prices.append({
                'currency': price.currency,
                'selected': is_selected,
            })

    # If no currency matched the lang_currency, select the first one
    if not selected_set and prices:
        prices[0]['selected'] = True

    return {'prices': prices}


@register.simple_tag()
def render_localized_price(entity):
    """
    Renders the price of an entity (Room, Reservation, Payment) based on the context.

    Logic:
    1. If entity has 'prices' list (e.g. Room):
       - Detect user's language/currency.
       - Select the matching price from the list.
       - Fallback to active price if specific currency not found.
    2. If entity has 'price' and 'currency' (e.g. Reservation, Payment):
       - Use the stored price and currency directly (historical accuracy).

    Returns formatted string (e.g., "R$ 200.00") or empty string if no price found.
    """
    selected_price_value = None
    selected_currency = None

    # Case 1: Entity is likely a Room (has list of prices)
    if hasattr(entity, 'prices'):
        prices = entity.prices
        # Handle Django ManyRelatedManager
        if isinstance(prices, Manager) or hasattr(prices, 'all'):
            prices = prices.all()

        # We need to select the right price based on user's language
        current_lang = get_language()
        target_currency = get_currency_for_language_code(current_lang)

        # Try to find exact currency match
        active_prices = filter(lambda p: p.active, prices)
        for price in active_prices:
            if price.currency == target_currency:
                selected_price_value = price.value
                selected_currency = price.currency
                break

        # Fallback: find any active price if no match found
        if selected_price_value is None:
            for price in active_prices:
                selected_price_value = price.value
                selected_currency = price.currency
                break

    # Case 2: Entity is likely a Reservation or Payment (has specific price/currency)
    elif hasattr(entity, 'price') and hasattr(entity, 'currency'):
        selected_price_value = entity.price
        selected_currency = entity.currency

    # Price entity
    elif hasattr(entity, 'value') and hasattr(entity, 'currency'):
        selected_price_value = entity.value
        selected_currency = entity.currency

    if selected_price_value is None or selected_currency is None:
        return ''

    # Format the output
    # Price is stored in cents
    try:
        value_float = selected_price_value / 100.0
    except (TypeError, ValueError):
        return ''  # Handle cases where price might be None or invalid

    symbol = get_currency_symbol(selected_currency)

    # Basic formatting: 1,234.56
    return f'{symbol} {value_float:,.2f}'
