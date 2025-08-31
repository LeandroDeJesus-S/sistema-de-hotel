class PaymentErrorMessages:
    INVALID_PAYMENT_VALUE = 'Valor de pagamento inválido'


class CheckoutMessages:
    TRANSACTION_BLOCKING = (
        'Não foi possível prosseguir para o pagamento ou quarto não esta mais disponível.'
    )
    PAYMENT_FAIL = (
        'Não foi possível concluir o pagamento devido a um erro inesperado '
        'tente novamente ou contate o suporte caso o problema persista.'
    )


class PaymentCancelMessages:
    PAYMENT_DOES_NOT_EXISTS = 'Pagamento não existe.'
    UNEXPECTED_ERROR = (
        'Tivemos um erro inesperado. Tente novamente mais tarde ou contate o desenvolvedor.'
    )
