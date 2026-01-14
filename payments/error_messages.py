from django.utils.translation import gettext_lazy as _


class PaymentErrorMessages:
    INVALID_PAYMENT_VALUE = _('Invalid payment value')


class CheckoutMessages:
    TRANSACTION_BLOCKING = _('Could not proceed to payment or room is no longer available.')
    PAYMENT_FAIL = _(
        'Could not complete the payment due to an unexpected error '
        'please try again or contact support if the problem persists.'
    )


class PaymentCancelMessages:
    PAYMENT_DOES_NOT_EXISTS = _('Payment does not exist.')
    UNEXPECTED_ERROR = _(
        'We had an unexpected error. Please try again later or contact the developer.'
    )
