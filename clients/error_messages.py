from .rules import ClientRules


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


INVALID_RECAPTCHA_MESSAGE = 'Mr. Robot, é você???'


class SignUpMessages:
    MISSING_FIELDS = 'Ainda há campos não preenchidos.'
    DUPLICATED_USER = 'Usuário já existe.'
    INVALID_USERNAME = 'Nome de usuário inválido.'


class SignInMessages:
    INVALID_CREDENTIALS = 'Credenciais inválidas, tente novamente.'
    LOGIN_SUCCESS = 'Olá {username}, seja bem-vindo.'


class PerfilChangePasswordMessages:
    PASSWORDS_DIFFER = 'As senhas não são iguais.'
    SUCCESS = 'Senha alterada com sucesso.'
