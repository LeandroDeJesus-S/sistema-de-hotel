from datetime import datetime, timedelta

from django.core.exceptions import ValidationError


def validate_fullname(name: str):
    MIN_CHAR_REQUIRED = 2
    
    words = name.split()
    n_words = len(words)
    len_words = [len(w) for w in words]
    
    if n_words < MIN_CHAR_REQUIRED:
        raise ValidationError('Insira seu nome completo!')
    
    for l in len_words:
        if l < MIN_CHAR_REQUIRED:
            raise ValidationError('Insira um nome válido!')
        
    
def validate_checkin_and_checkout(checkin: str, checkout: str):
    MIN_DAYS, MAX_DAYS = 2, 30
    
    chk_in = datetime.strptime(checkin, '%Y-%m-%d')
    chkout = datetime.strptime(checkout, '%Y-%m-%d')
    
    if chk_in > chkout:
        raise ValidationError('Data de Check-in ou Checkout inválida!')

    estadia = chkout - chk_in
    if estadia.days < MIN_DAYS or estadia.days > MAX_DAYS:
        raise ValidationError('A estadia deve ser de 2 a 30 dias.')


def validate_qtd_adultos(qtd_adults: int, room_type: str):
    if room_type.lower() in ['básico', 'luxo'] and qtd_adults > 3:
        raise ValidationError('Capacidade maxima de adultos ultrapassada.')
    