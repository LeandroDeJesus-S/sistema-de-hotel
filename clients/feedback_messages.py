from django.utils.translation import gettext_lazy as _


class Generic:
    UNEXPECTED_ERROR = _('Ocorreu um erro inesperado. Por favor, tente novamente mais tarde.')
    INVALID_DATA = _('Dados inválidos.')


class Recaptcha:
    INVALID_MESSAGE = _('Captcha inválido, por favor, tente novamente.')


class SignUp:
    MISSING_FIELDS = _('Ainda há campos não preenchidos.')
    DUPLICATED_USER = _('Usuário já existe.')
    INVALID_USERNAME = _('Nome de usuário inválido.')


class SignIn:
    INVALID_CREDENTIALS = _('Credenciais inválidas, por favor, tente novamente.')
    LOGIN_SUCCESS = _('Olá %(username)s, seja bem-vindo.')
    LOCKOUT_MESSAGE = _(
        'Número de tentativas excedido. Por favor, tente novamente mais tarde.'
    )


class Profile:
    UPDATE_SUCCESS = _('Perfil atualizado com sucesso.')


class ChangePassword:
    PASSWORDS_DIFFER = _('As senhas não são as mesmas.')
    SUCCESS = _('Senha alterada com sucesso.')


class ClientErrorMessages:
    GENERIC = _('Dados de cliente inválidos.')
    SIGNUP_ERROR = _('Não foi possível criar a conta. Verifique seus dados e tente novamente.')

    DUPLICATED_CPF = _('CPF não disponível.')
    DUPLICATED_USERNAME = _('Nome de usuário já existe.')

    INVALID_BIRTHDATE = _('Data de nascimento inválida.')
    INVALID_CPF = _('CPF inválido.')
    INVALID_EMAIL = _('E-mail inválido.')
    INVALID_FIRSTNAME_MAX_LENGTH = _('Nome muito longo.')
    INVALID_FIRSTNAME_MIN_LENGTH = _('Nome muito curto.')
    INVALID_FIRSTNAME_LETTERS = _('O nome deve conter apenas letras.')
    INVALID_SURNAME_MAX_LENGTH = _('Sobrenome muito longo.')
    INVALID_SURNAME_MIN_LENGTH = _('Sobrenome muito curto.')
    INVALID_SURNAME_LETTERS = _('O sobrenome deve conter apenas letras e espaços.')
    INVALID_USERNAME_CHARS = _(
        'Por favor, insira um nome de usuário válido. O valor deve conter apenas letras, '
        'números e os seguintes caracteres @.+-_'
    )
    INVALID_USERNAME_MIN_LEN = _(
        'O nome de usuário deve ter pelo menos %(limit_value)d caracteres.'
    )
    INVALID_USERNAME_MAX_LEN = _(
        'O nome de usuário deve ter no máximo %(limit_value)d caracteres.'
    )
    INVALID_USERNAME_LEN = _(
        'O nome de usuário deve ter de %(min_len)d a %(max_len)d caracteres.'
    )

    NOT_PROVIDED_EMAIL = _('Por favor, preencha o campo de e-mail.')
    NOT_PROVIDED_USERNAME = _('O nome de usuário não pode estar vazio.')
    NOT_PROVIDED_PHONE = _('O telefone não pode estar vazio.')

    PASSWORD_WEAK = _(
        'A senha deve conter pelo menos %(min_len)d dígitos, letras,'
        ' números e alguns dos símbolos %(symbols)s'
    )


class ContactErrorMessages:
    GENERIC = _('Dados de contato inválidos.')
    DUPLICATED_PHONE = _('Número de telefone não disponível.')
    DUPLICATED_EMAIL = _('E-mail não disponível.')

    INVALID_PHONE = _('Número de telefone inválido.')
    INVALID_EMAIL = _('Por favor, insira um endereço de e-mail válido.')
