from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from secrets import token_hex
from payments.models import Pagamento
from django.conf import settings
import io
from django.core.mail import EmailMessage
from django.urls import reverse
from .supportviews import ReservaSupport
from django.utils.timezone import now, timedelta
import stripe
from stripe.checkout import Session
from typing import Any

RESERVATION_PATIENCE_MINUTES = 30  # dependent of stipe :(


class PaymentPDFHandler:
    def __init__(self, payment: Pagamento) -> None:
        self.payment = payment
        self._pdf_suffix = token_hex(16)
        self.pdf_name = f'comprovante_de_pagamento_{self.payment.pk}.pdf'
        y = A4[1] * .5
        self.pagesize = (A4[0], y)
        self.buffer = io.BytesIO()
        self._canvas = canvas.Canvas(self.buffer, pagesize=self.pagesize)
        self.w, self.h = self.pagesize
    
    def handle(self):
        self._draw_header()
        self._draw_body()
        self._save()
        self._send_email()
        
    def _rows_list(self):
        rows = [
            f'Data de emissão: {self.payment.data.strftime("%h:%M:%S %d/%m/%Y")}',
            f'Status: {self.payment.status}',
            f'Pagador: {self.payment.reserva.cliente.complete_name}',
            f'Recebedor: HOTEL'
            f'Check-in: {self.payment.reserva.check_in.strftime("%d/%m/%Y")}',
            f'Check-out: {self.payment.reserva.checkout.strftime("%d/%m/%Y")}',
            f'Classe: {self.payment.reserva.quarto.classe}',
            f'Quarto: Nº{self.payment.reserva.quarto.numero}',
            f'Total: {self.payment.reserva.formatted_price()}',
        ]
        return rows
    
    def _draw_header(self):
        self._canvas.drawInlineImage(str(settings.SITE_LOGO_ICON), 30, self.h-40)

        self._canvas.setFontSize(30)
        self._canvas.drawString(65, self.h-38, settings.SITE_NAME)

        self._canvas.setFontSize(20)
        self._canvas.drawString(self.w-350, self.h-40, 'COMPROVANTE DE PAGAMENTO', wordSpace=0.5)

        self._canvas.line(30, self.h-50, self.w-30, self.h-50)
    
    def _draw_body(self):
        self._canvas.setFontSize(15)
        initial_offset = 85
        offset_y = initial_offset
        for row in self._rows_list():
            self._canvas.drawString(70, self.h-offset_y, row)
            offset_y += initial_offset * .5

    def _save(self):
        self._canvas.save()
        self.buffer.seek(0)

    def _send_email(self):
        msg = EmailMessage(
            subject='Comprovante de pagamento  da reserva',
            body=f'Seu comprovante de pagamento para a reserva do quarto Nº{self.payment.reserva.quarto.numero}',
            to=[self.payment.reserva.cliente.email],
            from_email=settings.DEFAULT_FROM_EMAIL,
        )
        msg.attach(self.pdf_name, self.buffer.getvalue(), 'application/pdf')
        msg.send(fail_silently=False)


class ReservationStripePaymentCreator:
    """Cria a session para pagamento da reserva pelo stripe"""
    stripe.api_key = settings.STRIPE_API_KEY_SECRET

    def __init__(self, request, reservation, success_url_name, cancel_url_name) -> None:
        self.baseurl = f"http://{request.get_host()}"
        self.success_url = self.baseurl + reverse(success_url_name, args=(reservation.pk,))
        self.cancel_url = self.baseurl + reverse(cancel_url_name, args=(reservation.pk,))
        self.expires_at = int(
            (
                now()
                + timedelta(minutes=ReservaSupport.RESERVATION_PATIENCE_MINUTES)
            ).timestamp()
        )
        self.reservation = reservation

        params = self._create_params()
        self._session = self._create_session(**params)
    
    @property
    def session(self):
        return self._session

    def _create_params(self) -> dict[str, Any]:
        prod_name = f"Reserva: Quarto Nº{self.reservation.quarto.numero}, classe {self.reservation.quarto.classe}."
        params = {
            "mode": "payment",
            "success_url": self.success_url,
            "cancel_url": self.cancel_url,
            "expires_at": self.expires_at,
            "line_items": [
                {
                    "adjustable_quantity": {
                        "enabled": False,
                    },
                    "price_data": {
                        "currency": "brl",
                        "product_data": {
                            "name": prod_name,
                        },
                        "unit_amount": self.reservation.quarto.daily_price_in_cents,
                    },
                    "quantity": self.reservation.reservation_days,
                }
            ],
        }
        return params
    
    def _create_session(self, **params) -> Session:
        return Session.create(**params)
