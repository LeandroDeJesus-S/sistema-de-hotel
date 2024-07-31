from datetime import timedelta, datetime

# class SessionKeys:
#     CLIENT_ID = 'client_id'
#     ROOM_ID = 'room_id'
#     ROOM_CLASS_ID = 'room_class_id'
#     RESERVATION_ID = 'reservation_id'

#     @staticmethod
#     def all_keys(exclude=None):
#         if exclude is None:
#             exclude = []
        
#         return [k for k in dir(SessionKeys) if k.isupper() if k not in exclude]


class QuartoRules:
    IMAGE_SIZE = 560, 420
    IMAGE_AVAILABLE_FORMATS = ['jpg', 'png']
    MAX_ADULTS = 5
    MIN_ADULTS = 1
    MAX_CHILDREN = 3
    MIN_CHILDREN = 0
    MIN_SIZE = 2
    MAX_SIZE = 30
    MIN_DAILY_PRICE = 100
    MAX_DAILY_PRICE = 500


class QuartoErrorMessages:
    IMAGE_INVALID_FORMAT = f'Tipo de imagem não suportado. disponíveis: {QuartoRules.IMAGE_AVAILABLE_FORMATS}'
    IMAGE_INVALID_NAME = 'Nome de imagem inválido.'
    SHORT_DESC_INVALID = 'Descrição curta fornecida é inválida'
    
    ADULTS_INSUFFICIENT = f'Quantidade de adultos insuficiente. (min: {QuartoRules.MIN_ADULTS})'
    CHILD_INSUFFICIENT = f'Quantidade de crianças insuficiente. (min: {QuartoRules.MIN_CHILDREN})'
    SIZE_INSUFFICIENT = f'O quarto é muito pequeno. (min: {QuartoRules.MIN_SIZE})'
    PRICE_INSUFFICIENT = f'O valor do quarto deve ser de no mínimo R${QuartoRules.MIN_DAILY_PRICE:.2f}.'
    
    ADULTS_EXCEEDED = f'Quantidade de adultos excedida. (max: {QuartoRules.MAX_ADULTS})'
    CHILD_EXCEEDED = f'Quantidade de crianças excedida. (max: {QuartoRules.MAX_CHILDREN})'
    SIZE_EXCEEDED = f'O quarto é muito grande. (max: {QuartoRules.MAX_SIZE})'
    PRICE_EXCEEDED = f'O valor do quarto deve ser de no máximo R${QuartoRules.MAX_DAILY_PRICE:.2f}.'


class ClasseErrorMessages:
    INVALID_NAME = 'Nome da classe é inválido.'


class ClienteRules:
    MIN_AGE = 18
    MAX_AGE = 122
    MIN_FIRSTNAME_CHARS = 2
    MAX_FIRSTNAME_CHARS = 25
    MIN_SURNAME_CHARS = 2
    MAX_SURNAME_CHARS = 50

    PASSWORD_SUPPORTED_SYMBOLS = "@<>();'-+*;"
    PASSWORD_MIN_SIZE = 8

    PHONE_MASK_RANGE = 4, -4  # ends must be negative
    EMAIL_MASK_RANGE = 2, -2

    USERNAME_MIN_SIZE = 2
    USERNAME_MAX_SIZE = 150


class ClienteErrorMessages:
    GENERIC = 'Dados de cliente inválidos'
    INVALID_NAME_MIN_LENGTH = 'Nome muito pequeno.'
    INVALID_NAME_MAX_LENGTH = 'Nome muito grande.'
    INVALID_SURNAME_MIN_LENGTH = 'Sobrenome muito pequeno.'
    INVALID_SURNAME_MAX_LENGTH = 'Sobrenome muito grande.'
    INVALID_BIRTHDATE = 'Data de nascimento inválida.'
    INVALID_NAME_LETTERS = 'O nome deve conter apenas letras'
    INVALID_SURNAME_LETTERS = 'O sobrenome deve conter apenas letras'
    DUPLICATED_USERNAME = 'Username já existe.'
    NOT_PROVIDED_EMAIL = 'Por favor, preencha o campo de email.'
    INVALID_EMAIL = 'E-mail inválido.'

    INVALID_USERNAME_CHARS = (
        'Informe um nome de usuário válido. O valor deve conter apenas letras, '
        'números e os seguintes caracteres @.+-_'
    )
    INVALID_USERNAME_LEN = (
        f'Nome de usuário deve ter de {ClienteRules.USERNAME_MIN_SIZE} '
        f'a {ClienteRules.USERNAME_MAX_SIZE} caracteres.'
    )
    PASSWORD_WEAK = (
        f'A senha de conter no mínimo {ClienteRules.PASSWORD_MIN_SIZE} dígitos, letras,'
        f' números e algum dos símbolos {ClienteRules.PASSWORD_SUPPORTED_SYMBOLS}'
    )


class ContatoErrorMessages:
    GENERIC = 'Dados de contato inválidos'
    INVALID_PHONE = 'Número de telefone inválido.'
    INVALID_EMAIL = 'Informe um endereço de email válido.'


class ReservaRules:
    MIN_RESERVATION_DAYS = 1
    MAX_RESERVATION_DAYS = 30
    ANTICIPATED_MONTHS_CHECKIN = 3

    @classmethod
    def checkin_anticipation_offset(cls):
        return (datetime.now() + timedelta(weeks=4 * cls.ANTICIPATED_MONTHS_CHECKIN)).date()


class ReservaErrorMessages:
    GENERIC = 'Dados de reserva inválidos'
    INVALID_CHECKIN_DATE = 'Data de check-in inválida'
    INVALID_CHECKIN_ANTICIPATION = f'Só é possível fazer reserva com até {ReservaRules.ANTICIPATED_MONTHS_CHECKIN} meses.'
    UNAVAILABLE_ROOM = 'Este quarto não esta disponível.'
    INVALID_STAYED_DAYS = (f'A reserva deve ter de {ReservaRules.MIN_RESERVATION_DAYS}'
                                        f' a {ReservaRules.MAX_RESERVATION_DAYS} dias.')
    INVALID_ROOM_CHOICE = 'Por favor, escolha um quarto válido.'
    UNAVAILABLE_DATE = 'Data de reserva indisponível. A datas disponíveis são {dates}'


class PaymentRules:
    ALLOWED_METHODS = ['card', 'boleto']


class PaymentErrorMessages:
    INVALID_PAYMENT_VALUE = 'Valor de pagamento inválido'
