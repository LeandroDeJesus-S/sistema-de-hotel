from datetime import datetime, date


def convert_date(value: str) -> date:
    """converte uma data em string para `datetime.date`. Caso
    o formato da data seja inválido e gere um ValueError
    retorna a data 1-1-1
    
    Args:
        value (str): data em string
    
    Returns:
        datetime.date: instancia de `datetime.date` da data formatada
    """
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return datetime(1,1,1).date()
