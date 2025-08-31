from .rules import ReserveRules, RoomRules


class BenefitErrorMessages:
    INVALID_ICON_SIZE = 'O ícone deve ter tamanho 64x64.'


class RoomErrorMessages:
    IMAGE_INVALID_FORMAT = (
        f'Tipo de imagem não suportado. disponíveis: {RoomRules.IMAGE_AVAILABLE_FORMATS}'
    )
    IMAGE_INVALID_NAME = 'Nome de imagem inválido.'
    SHORT_DESC_INVALID = 'Descrição curta fornecida é inválida'

    ADULTS_INSUFFICIENT = f'Quantidade de adultos insuficiente. (min: {RoomRules.MIN_ADULTS})'
    CHILD_INSUFFICIENT = (
        f'Quantidade de crianças insuficiente. (min: {RoomRules.MIN_CHILDREN})'
    )
    SIZE_INSUFFICIENT = f'O quarto é muito pequeno. (min: {RoomRules.MIN_SIZE})'
    PRICE_INSUFFICIENT = (
        f'O valor do quarto deve ser de no mínimo R${RoomRules.MIN_DAILY_PRICE:.2f}.'
    )

    ADULTS_EXCEEDED = f'Quantidade de adultos excedida. (max: {RoomRules.MAX_ADULTS})'
    CHILD_EXCEEDED = f'Quantidade de crianças excedida. (max: {RoomRules.MAX_CHILDREN})'
    SIZE_EXCEEDED = f'O quarto é muito grande. (max: {RoomRules.MAX_SIZE})'
    PRICE_EXCEEDED = (
        f'O valor do quarto deve ser de no máximo R${RoomRules.MAX_DAILY_PRICE:.2f}.'
    )


class ClasseErrorMessages:
    INVALID_NAME = 'Nome da classe é inválido.'


class ReserveErrorMessages:
    GENERIC = 'Dados de reserva inválidos'
    INVALID_CHECKIN_DATE = 'Data de check-in inválida'
    INVALID_CHECKIN_ANTICIPATION = (
        f'Só é possível fazer reserva com até {ReserveRules.ANTICIPATED_MONTHS_CHECKIN} meses.'
    )
    UNAVAILABLE_ROOM = 'Este quarto não esta disponível.'
    INVALID_STAYED_DAYS = (
        f'A reserva deve ter de {ReserveRules.MIN_RESERVATION_DAYS}'
        f' a {ReserveRules.MAX_RESERVATION_DAYS} dias.'
    )
    INVALID_ROOM_CHOICE = 'Por favor, escolha um quarto válido.'
    UNAVAILABLE_DATE = 'Data de reserva indisponível. A datas disponíveis são {dates}'


class ReserveMessages:
    RESERVATION_FAIL = 'Não foi possível realizar a reserva.'
    ALREADY_HAVE_A_RESERVATION = 'Você já possui uma reserva ativa ou agendada'
