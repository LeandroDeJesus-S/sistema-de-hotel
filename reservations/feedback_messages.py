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
    RESERVATION_NOT_FOUND = _('Reserva não encontrada.')
    CANCELED_SUCCESS = _('Reserva cancelada com sucesso.')
    CANCEL_ERROR = _('Não foi possível cancelar a reserva.')
    RESERVATION_FAIL = _('Não foi possível realizar a reserva.')
    ALREADY_HAVE_A_RESERVATION = _('Você já possui uma reserva ativa ou agendada')
    UNAUTHORIZED_CANCELLATION = _('Você não tem permissão para cancelar esta reserva.')
    CANNOT_CANCEL_RESERVATION = _('Esta reserva não pode ser cancelada.')
    CANCELLATION_TOO_LATE = _(
        'Cancelamentos só são permitidos até 24 horas antes do check-in.'
    )


class BenefitErrorMessages:
    INVALID_ICON_SIZE = _('O ícone deve ter tamanho 64x64.')
    NAME_EMPTY = _('O nome do benefício não pode ser vazio.')
    ICON_EMPTY = _('O ícone do benefício não pode ser vazio.')
    SHORT_DESC_EMPTY = _('A descrição curta do benefício não pode ser vazia.')
    INVALID_PATTERN = _('O nome do benefício não pode conter caracteres especiais.')


class RoomErrorMessages:
    IMAGE_INVALID_FORMAT = _(
        'Tipo de imagem não suportado. disponíveis: %(available_formats)s'
    ) % {'available_formats': RoomRules.IMAGE_AVAILABLE_FORMATS}
    IMAGE_INVALID_NAME = _('Nome de imagem inválido.')
    SHORT_DESC_INVALID = _('Descrição curta fornecida é inválida')

    ADULTS_INSUFFICIENT = _('Quantidade de adultos insuficiente. (min: %(min_adults)s)') % {
        'min_adults': RoomRules.MIN_ADULTS
    }
    CHILD_INSUFFICIENT = _('Quantidade de crianças insuficiente. (min: %(min_children)s)') % {
        'min_children': RoomRules.MIN_CHILDREN
    }
    SIZE_INSUFFICIENT = _('O quarto é muito pequeno. (min: %(min_size)s)') % {
        'min_size': RoomRules.MIN_SIZE
    }
    PRICE_INSUFFICIENT = _(
        'O valor do quarto deve ser de no mínimo R$%(min_daily_price).2f.'
    ) % {'min_daily_price': RoomRules.MIN_DAILY_PRICE}

    ADULTS_EXCEEDED = _('Quantidade de adultos excedida. (max: %(max_adults)s)') % {
        'max_adults': RoomRules.MAX_ADULTS
    }
    CHILD_EXCEEDED = _('Quantidade de crianças excedida. (max: %(max_children)s)') % {
        'max_children': RoomRules.MAX_CHILDREN
    }
    SIZE_EXCEEDED = _('O quarto é muito grande. (max: %(max_size)s)') % {
        'max_size': RoomRules.MAX_SIZE
    }
    PRICE_EXCEEDED = _('O valor do quarto deve ser de no máximo R$%(max_daily_price).2f.') % {
        'max_daily_price': RoomRules.MAX_DAILY_PRICE
    }


class ClasseErrorMessages:
    INVALID_NAME = _('Nome da classe é inválido.')
    NAME_EMPTY = _('O nome da classe não pode ser vazio.')


class ReserveErrorMessages:
    GENERIC = _('Dados de reserva inválidos')
    INVALID_CHECKIN_DATE = _('Data de check-in inválida')
    INVALID_CHECKIN_ANTICIPATION = _('Só é possível fazer reserva com até %(date)s meses.') % {
        'date': ReserveRules.ANTICIPATED_MONTHS_CHECKIN
    }
    UNAVAILABLE_ROOM = _('Este quarto não esta disponível.')
    INVALID_STAYED_DAYS = _('A reserva deve ter de %(min_days)s a %(max_days)s dias.') % {
        'min_days': ReserveRules.MIN_RESERVATION_DAYS,
        'max_days': ReserveRules.MAX_RESERVATION_DAYS,
    }
    INVALID_ROOM_CHOICE = _('Por favor, escolha um quarto válido.')
    UNAVAILABLE_DATE = _('Data de reserva indisponível. A datas disponíveis são %(dates)s')
