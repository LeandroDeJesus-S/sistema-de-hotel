class SignUpMessages:
    MISSING = 'Ainda há campos não preenchidos.'
    DUPLICATED_USER = 'Usuário já existe.'
    INVALID_USERNAME = 'Nome de usuário inválido.'


class SignInMessages:
    INVALID_CREDENTIALS = 'Credenciais inválidas, tente novamente.'
    LOGIN_SUCCESS = 'Olá {username}, seja bem-vindo.'


class PerfilChangePasswordMessages:
    PASSWORDS_DIFFERS = 'As senhas não são iguais.'
    SUCCESS = 'Senha alterada com sucesso.'


class CheckoutMessages:
    TRANSACTION_BLOCKING = 'Não foi possível prosseguir para o pagamento ou quarto não esta mais disponível.'
    PAYMENT_FAIL = (
        'Não foi possível concluir o pagamento devido a um erro inesperado '
        'tente novamente ou contate o suporte caso o problema persista.'
    )


class ReserveSupport:
    RESERVATION_PATIENCE_MINUTES = 30  # dependent of stipe :(


class ReserveMessages:
    RESERVATION_FAIL = 'Não foi possível realizar a reserva.'
    ALREADY_HAVE_A_RESERVATION = 'Você já possui uma reserva ativa ou agendada'


class PaymentCancelMessages:
    PAYMENT_DOES_NOT_EXISTS = 'Pagamento não existe.'
    UNEXPECTED_ERROR = 'Tivemos um erro inesperado. Tente novamente mais tarde ou contate o desenvolvedor.'
