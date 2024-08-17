from datetime import timedelta, datetime


class BenefitRules:
    ICON_SIZE = 64, 64

    
class BenefitErrorMessages:
    INVALID_ICON_SIZE = 'O ícone deve ter tamanho 64x64.'


class RoomRules:
    IMAGE_SIZE = 560, 420
    IMAGE_AVAILABLE_FORMATS = ['jpg', 'png']
    MAX_ADULTS = 5
    MIN_ADULTS = 1
    MAX_CHILDREN = 3
    MIN_CHILDREN = 0
    MAX_SIZE = 30
    MIN_SIZE = 2
    MAX_DAILY_PRICE = 500
    MIN_DAILY_PRICE = 100


class RoomErrorMessages:
    IMAGE_INVALID_FORMAT = f'Tipo de imagem não suportado. disponíveis: {RoomRules.IMAGE_AVAILABLE_FORMATS}'
    IMAGE_INVALID_NAME = 'Nome de imagem inválido.'
    SHORT_DESC_INVALID = 'Descrição curta fornecida é inválida'
    
    ADULTS_INSUFFICIENT = f'Quantidade de adultos insuficiente. (min: {RoomRules.MIN_ADULTS})'
    CHILD_INSUFFICIENT = f'Quantidade de crianças insuficiente. (min: {RoomRules.MIN_CHILDREN})'
    SIZE_INSUFFICIENT = f'O quarto é muito pequeno. (min: {RoomRules.MIN_SIZE})'
    PRICE_INSUFFICIENT = f'O valor do quarto deve ser de no mínimo R${RoomRules.MIN_DAILY_PRICE:.2f}.'
    
    ADULTS_EXCEEDED = f'Quantidade de adultos excedida. (max: {RoomRules.MAX_ADULTS})'
    CHILD_EXCEEDED = f'Quantidade de crianças excedida. (max: {RoomRules.MAX_CHILDREN})'
    SIZE_EXCEEDED = f'O quarto é muito grande. (max: {RoomRules.MAX_SIZE})'
    PRICE_EXCEEDED = f'O valor do quarto deve ser de no máximo R${RoomRules.MAX_DAILY_PRICE:.2f}.'


class ClasseErrorMessages:
    INVALID_NAME = 'Nome da classe é inválido.'


class ClientRules:
    MAX_AGE = 122
    MIN_AGE = 18
    MAX_FIRSTNAME_CHARS = 25
    MIN_FIRSTNAME_CHARS = 2
    MAX_SURNAME_CHARS = 50
    MIN_SURNAME_CHARS = 2

    PASSWORD_SUPPORTED_SYMBOLS = "@<>();'-+*;"
    PASSWORD_MIN_SIZE = 8

    CPF_MASK_RANGE = 2, -4
    EMAIL_MASK_RANGE = 2, -2
    PHONE_MASK_RANGE = 4, -4  # ends must be negative

    USERNAME_MAX_SIZE = 150
    USERNAME_MIN_SIZE = 2


class ClientErrorMessages:
    GENERIC = 'Dados de cliente inválidos'
    
    DUPLICATED_CPF = 'CPF não disponível.'
    DUPLICATED_USERNAME = 'Username já existe.'
    
    INVALID_BIRTHDATE = 'Data de nascimento inválida.'
    INVALID_CPF = 'CPF inválido.'
    INVALID_EMAIL = 'E-mail inválido.'
    INVALID_FIRSTNAME_MAX_LENGTH = 'Nome muito grande.'
    INVALID_FIRSTNAME_MIN_LENGTH = 'Nome muito pequeno.'
    INVALID_FIRSTNAME_LETTERS = 'O nome deve conter apenas letras'
    INVALID_SURNAME_MAX_LENGTH = 'Sobrenome muito grande.'
    INVALID_SURNAME_MIN_LENGTH = 'Sobrenome muito pequeno.'
    INVALID_SURNAME_LETTERS = 'O sobrenome deve conter apenas letras e espaços'
    INVALID_USERNAME_CHARS = (
        'Informe um nome de usuário válido. O valor deve conter apenas letras, '
        'números e os seguintes caracteres @.+-_'
    )
    INVALID_USERNAME_LEN = (
        f'Nome de usuário deve ter de {ClientRules.USERNAME_MIN_SIZE} '
        f'a {ClientRules.USERNAME_MAX_SIZE} caracteres.'
    )
    
    NOT_PROVIDED_EMAIL = 'Por favor, preencha o campo de email.'
    NOT_PROVIDED_USERNAME = 'Nome de usuário não pode ser vazio.'
    NOT_PROVIDED_PHONE = 'Telefone não pode ser vazio.'

    PASSWORD_WEAK = (
        f'A senha de conter no mínimo {ClientRules.PASSWORD_MIN_SIZE} dígitos, letras,'
        f' números e algum dos símbolos {ClientRules.PASSWORD_SUPPORTED_SYMBOLS}'
    )


class ContactErrorMessages:
    GENERIC = 'Dados de contato inválidos'
    DUPLICATED_PHONE = 'Telefone não disponível.'
    DUPLICATED_EMAIL = 'E-mail não disponível.'

    INVALID_PHONE = 'Número de telefone inválido.'
    INVALID_EMAIL = 'Informe um endereço de email válido.'


class ReserveRules:
    MIN_RESERVATION_DAYS = 1
    MAX_RESERVATION_DAYS = 30
    ANTICIPATED_MONTHS_CHECKIN = 3

    @classmethod
    def checkin_anticipation_offset(cls):
        return (datetime.now() + timedelta(weeks=4 * cls.ANTICIPATED_MONTHS_CHECKIN)).date()


class ReserveErrorMessages:
    GENERIC = 'Dados de reserva inválidos'
    INVALID_CHECKIN_DATE = 'Data de check-in inválida'
    INVALID_CHECKIN_ANTICIPATION = f'Só é possível fazer reserva com até {ReserveRules.ANTICIPATED_MONTHS_CHECKIN} meses.'
    UNAVAILABLE_ROOM = 'Este quarto não esta disponível.'
    INVALID_STAYED_DAYS = (f'A reserva deve ter de {ReserveRules.MIN_RESERVATION_DAYS}'
                                        f' a {ReserveRules.MAX_RESERVATION_DAYS} dias.')
    INVALID_ROOM_CHOICE = 'Por favor, escolha um quarto válido.'
    UNAVAILABLE_DATE = 'Data de reserva indisponível. A datas disponíveis são {dates}'


class PaymentRules:
    ALLOWED_METHODS = ['card', 'boleto']


class PaymentErrorMessages:
    INVALID_PAYMENT_VALUE = 'Valor de pagamento inválido'


class ServicesRules:
    IMG_SIZE = 720, 480
