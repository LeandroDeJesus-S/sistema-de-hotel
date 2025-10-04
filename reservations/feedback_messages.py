from django.utils.translation import gettext_lazy as _

from .rules import ReserveRules, RoomRules


class Generic:
    UNEXPECTED_ERROR = _('Ocorreu um erro inesperado. Por favor, tente novamente mais tarde.')
    INVALID_DATA = _('Dados inválidos.')


class ReservationMessages:
    UNAVAILABLE_ROOM = _('O quarto não está disponível para as datas selecionadas.')
    INVALID_DATE_RANGE = _('A data de check-out deve ser posterior à data de check-in.')
    SUCCESS = _('Reserva realizada com sucesso.')
    NOT_FOUND = _('Reserva não encontrada.')
    CANCELED_SUCCESS = _('Reserva cancelada com sucesso.')
    CANCEL_ERROR = _('Não foi possível cancelar a reserva.')
    RESERVATION_FAIL = _('Não foi possível realizar a reserva.')
    ALREADY_HAVE_A_RESERVATION = _('Você já possui uma reserva ativa ou agendada')


class BenefitErrorMessages:
    INVALID_ICON_SIZE = _('O ícone deve ter tamanho 64x64.')
    NAME_EMPTY = _('O nome do benefício não pode ser vazio.')
    ICON_EMPTY = _('O ícone do benefício não pode ser vazio.')
    SHORT_DESC_EMPTY = _('A descrição curta do benefício não pode ser vazia.')
    INVALID_PATTERN = _('O nome do benefício não pode conter caracteres especiais.')


class RoomErrorMessages:
    IMAGE_INVALID_FORMAT = (
        f'Tipo de imagem não suportado. disponíveis: {RoomRules.IMAGE_AVAILABLE_FORMATS}'
    )
    IMAGE_INVALID_NAME = _('Nome de imagem inválido.')
    SHORT_DESC_INVALID = _('Descrição curta fornecida é inválida')

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
    INVALID_NAME = _('Nome da classe é inválido.')
    NAME_EMPTY = _('O nome da classe não pode ser vazio.')


class ReserveErrorMessages:
    GENERIC = _('Dados de reserva inválidos')
    INVALID_CHECKIN_DATE = _('Data de check-in inválida')
    INVALID_CHECKIN_ANTICIPATION = (
        f'Só é possível fazer reserva com até {ReserveRules.ANTICIPATED_MONTHS_CHECKIN} meses.'
    )
    UNAVAILABLE_ROOM = _('Este quarto não esta disponível.')
    INVALID_STAYED_DAYS = (
        f'A reserva deve ter de {ReserveRules.MIN_RESERVATION_DAYS}'
        f' a {ReserveRules.MAX_RESERVATION_DAYS} dias.'
    )
    INVALID_ROOM_CHOICE = _('Por favor, escolha um quarto válido.')
    UNAVAILABLE_DATE = _('Data de reserva indisponível. A datas disponíveis são {dates}')
