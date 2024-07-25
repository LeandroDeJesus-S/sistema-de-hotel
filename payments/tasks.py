from utils.support import PaymentPDFHandler


def create_payment_pdf(payment):
    pdf_handler = PaymentPDFHandler(payment)
    pdf_handler.handle()
