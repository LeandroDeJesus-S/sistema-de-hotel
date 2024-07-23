class SignUpMessages:
    MISSING = 'Ainda há campos não preenchidos.'
    DUPLICATED_USER = 'Usuário já existe.'
    INVALID_USERNAME = 'Nome de usuário inválido.'


class SignInMessages:
    INVALID_CREDENTIALS = 'Credenciais inválidas, tente novamente.'
    LOGIN_SUCCESS = 'Olá {username}, seja bem-vindo.'


class PaymentMessages:
    PAYMENT_FAIL = (
        'Não foi possível concluir o pagamento devido a um erro com o sistema de '
        'pagamento externo, tente novamente ou contate o suporte caso o problema persista.'
    )