class SignUpMessages:
    MISSING = 'Ainda há campos não preenchidos.'
    DUPLICATED_USER = 'Usuário já existe.'
    INVALID_USERNAME = 'Nome de usuário inválido.'


class SignInMessages:
    INVALID_CREDENTIALS = 'Credenciais inválidas, tente novamente.'
    LOGIN_SUCCESS = 'Olá {username}, seja bem-vindo.'


class CheckoutMessages:
    TRANSACTION_BLOCKING = 'Não foi possível prosseguir para o pagamento ou quarto não esta mais disponível.'
    PAYMENT_FAIL = (
        'Não foi possível concluir o pagamento devido a um erro com o sistema de '
        'pagamento externo, tente novamente ou contate o suporte caso o problema persista.'
    )


class ReserveSupport:
    RESERVATION_PATIENCE_MINUTES = 30  # dependent of stipe :(


class ReserveMessages:
    RESERVATION_FAIL = 'Não foi possível realizar a reserva.'
    ALREADY_HAVE_A_RESERVATION = 'Você já possui uma reserva ativa ou agendada'
