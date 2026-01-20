import re


def sanitize_digits(value: str) -> str:
    """Removes non-digit characters from a string.
    Args:
        value (str): The string to sanitize.
    Returns:
        str: The sanitized string containing only digits.
    """
    return re.sub(r'\D', '', value)
