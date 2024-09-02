from utils.support import PaymentPDFHandler


def create_payment_pdf(payment) -> bool:
    """generate a PDf file with the payment data and sent by email
    to the user
    
    Args:
        payment (Payment): instance of the model Payment.
    
    Returns:
        bool: returns True if the email was sent correctly
    """
    pdf_handler = PaymentPDFHandler(payment)
    log = pdf_handler.handle()
    return True if log else False
