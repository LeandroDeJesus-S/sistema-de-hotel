from datetime import date, datetime

from utils.decorators import ensure_result


@ensure_result
def convert_date(value: str) -> date:
    """converte uma data em string para `datetime.date`. Caso
    o formato da data seja inválido e gere um ValueError
    retorna a data 1-1-1

    Args:
        value (str): data em string

    Returns:
        datetime.date: instancia de `datetime.date` da data formatada
    """
    return datetime.strptime(value, '%Y-%m-%d').date()
