from typing import Optional

from base.ports.email import AbsEmailSender
from base.ports.pdf import AbsPDFGenerator
from exc import Result
from payments.application.usecases import SendPaymentConfirmationUseCase
from payments.domain.ports import AbsPaymentsRepository
from payments.infra.repo import PaymentRepository
from utils.adapters.email import DjangoEmailSender
from utils.adapters.pdf import ReportLabPDFReceiptGenerator


def get_payment_repository() -> AbsPaymentsRepository:
    return PaymentRepository()


def get_pdf_generator() -> AbsPDFGenerator:
    return ReportLabPDFReceiptGenerator()


def get_email_sender() -> AbsEmailSender:
    return DjangoEmailSender()


# XXX: you've finished to fix broken tests, now you should test if the live app works
def send_payment_confirmation(
    payment_id: int,
    payment_repo: Optional[AbsPaymentsRepository] = None,
    pdf_generator: Optional[AbsPDFGenerator] = None,
    email_sender: Optional[AbsEmailSender] = None,
) -> Result[None]:
    """
    Sends a payment confirmation email to the client.

    This task generates a PDF receipt for the payment and attaches it to the email.

    Args:
        payment_id: The ID of the payment to confirm.
        pdf_generator: Optional. The PDF generator to use. Defaults to
            ReportLabPDFReceiptGenerator.
        email_sender: Optional. The email sender to use. Defaults to DjangoEmailSender.
        payment_repo: Optional. The payment repository to use. Defaults to PaymentRepository.

    Returns:
        A Result indicating success or failure.
    """
    payment_repo = payment_repo or get_payment_repository()
    pdf_generator = pdf_generator or get_pdf_generator()
    email_sender = email_sender or get_email_sender()
    usecase = SendPaymentConfirmationUseCase(
        mailer=email_sender,
        pdf_generator=pdf_generator,
    )

    payment_result = payment_repo.get_by_id(payment_id)
    if payment_result.is_err():
        raise Result.Err(f'Payment with id {payment_id} not found.').unwrap_err()

    payment = payment_result.unwrap()
    res = usecase(payment)
    if res.is_err():
        raise Result.Err(res.unwrap_err().msg).unwrap_err()

    return Result.Ok(None)
