import io
import os

from django.conf import settings
from django.utils.translation import activate
from django.utils.translation import gettext as _
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from base.ports.pdf import AbsPDFGenerator
from exc import Result
from home.domain.entities import Hotel
from payments.domain.entities import Payment


class ReportLabPDFReceiptGenerator(AbsPDFGenerator):
    """A PDF generator adapter that uses the ReportLab library."""

    def generate(self, payment: Payment, locale: str = 'en') -> Result[bytes]:
        """Generates a payment receipt PDF using ReportLab.

        Args:
            payment: The payment object containing the data for the receipt.
            locale: The locale code for PDF content translation.

        Returns:
            The generated PDF as bytes.
        """

        try:
            activate(locale)
            hotel = payment.reservation.room.hotel

            buffer = io.BytesIO()
            y = A4[1] * 0.5
            pagesize = (A4[0], y)
            w, h = pagesize

            pdf_canvas = canvas.Canvas(buffer, pagesize=pagesize)

            self._draw_header(pdf_canvas, hotel, w, h)
            self._draw_body(pdf_canvas, payment, h)

            pdf_canvas.save()
            buffer.seek(0)
            return Result.Ok(buffer.getvalue())
        except Exception as e:
            return Result.Err(msg='Failed to generate PDF', src_error=e)

    def _draw_header(  # noqa: PLR6301
        self, pdf_canvas: canvas.Canvas, hotel: Hotel, w: int, h: int
    ) -> None:
        """draw the logo, hotel name, and title of the pdf"""
        if hotel.logo:
            pdf_canvas.drawInlineImage(
                os.path.join(settings.MEDIA_URL, hotel.logo), 30, h - 40
            )

        pdf_canvas.setFontSize(30)
        pdf_canvas.drawString(65, h - 38, hotel.name)

        pdf_canvas.setFontSize(20)
        pdf_canvas.drawString(
            w - 350,
            h - 40,
            _('Payment Receipt'),
            wordSpace=0.5,
        )

        pdf_canvas.line(30, h - 50, w - 30, h - 50)

    def _draw_body(self, pdf_canvas: canvas.Canvas, payment: Payment, h: float) -> None:
        """draw the payment information into the body of the pdf"""
        pdf_canvas.setFontSize(15)
        initial_offset = 85.0
        offset_y = initial_offset
        for row in self._rows_list(payment):
            pdf_canvas.drawString(70, h - offset_y, row)
            offset_y += initial_offset * 0.5

    def _rows_list(self, payment: Payment) -> list[str]:  # noqa: PLR6301
        """return all the rows of the pdf in list format"""
        rows = [
            f'{_("Issue Date")}: {payment.created_at.strftime("%h:%M:%S %d/%m/%Y")}',
            f'{_("Status")}: {payment.status}',
            (
                f'{_("Payer")}: {payment.reservation.client.first_name} '
                f'{payment.reservation.client.last_name}'
            ),
            f'{_("Receiver")}: {_("HOTEL")}',
            f'{_("Check-in")}: {payment.reservation.checkin.strftime("%d/%b/%Y %H:%M")}',
            f'{_("Check-out")}: {payment.reservation.checkout.strftime("%d/%b/%Y %H:%M")}',
            f'{_("Class")}: {payment.reservation.room.room_class}',
            f'{_("Room")}: Nº{payment.reservation.room.number}',
            f'{_("Total")}: ${payment.reservation.amount:.2f}',
        ]
        return rows
