import requests
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from secrets import token_hex
from payments.models import Payment
from django.conf import settings
import io
from django.core.mail import EmailMessage
from django.urls import reverse
from .supportviews import ReserveSupport
from django.utils.timezone import now, timedelta
import stripe
from stripe.checkout import Session
from typing import Any
from home.models import Hotel, Contact
from PIL import Image
from datetime import datetime, date


class PaymentPDFHandler:
    """Cria o pdf com dados do pagamento e envia para o cliente via email.
    """
    def __init__(self, payment: Payment, hotel_id=1) -> None:
        self.payment = payment
        self._pdf_suffix = token_hex(16)
        self.pdf_name = f'comprovante_de_pagamento_{self.payment.pk}.pdf'
        y = A4[1] * .5
        self.pagesize = (A4[0], y)
        self.buffer = io.BytesIO()
        self._canvas = canvas.Canvas(self.buffer, pagesize=self.pagesize)
        self.w, self.h = self.pagesize
        self.hotel = Hotel.objects.get(pk=hotel_id)
        self.hotel_contact = Contact.objects.get(hotel=self.hotel)
    
    def handle(self):
        """template method that generate the pdf and sent by email to the client"""
        self._draw_header()
        self._draw_body()
        self._save()
        return self._send_email()
        
    def _rows_list(self):
        """return all the rows of the pdf in list format"""
        rows = [
            f'Data de emissão: {self.payment.date.strftime("%h:%M:%S %d/%m/%Y")}',
            f'Status: {self.payment.status}',
            f'Pagador: {self.payment.reservation.client.complete_name}',
            f'Recebedor: HOTEL'
            f'Check-in: {self.payment.reservation.checkin.strftime("%d/%m/%Y")}',
            f'Check-out: {self.payment.reservation.checkout.strftime("%d/%m/%Y")}',
            f'Classe: {self.payment.reservation.room.room_class}',
            f'Quarto: Nº{self.payment.reservation.room.number}',
            f'Total: {self.payment.reservation.formatted_price()}',
        ]
        return rows
    
    def _draw_header(self):
        """draw the logo, hotel name, and title of the pdf"""
        if self.hotel.logo:
            self._canvas.drawInlineImage(str(self.hotel.logo.path), 30, self.h-40)

        self._canvas.setFontSize(30)
        self._canvas.drawString(65, self.h-38, self.hotel.name)

        self._canvas.setFontSize(20)
        self._canvas.drawString(self.w-350, self.h-40, 'COMPROVANTE DE PAGAMENTO', wordSpace=0.5)

        self._canvas.line(30, self.h-50, self.w-30, self.h-50)
    
    def _draw_body(self):
        """draw the payment information into the body of the pdf"""
        self._canvas.setFontSize(15)
        initial_offset = 85
        offset_y = initial_offset
        for row in self._rows_list():
            self._canvas.drawString(70, self.h-offset_y, row)
            offset_y += initial_offset * .5

    def _save(self):
        """save the generated pdf in the buffer"""
        self._canvas.save()
        self.buffer.seek(0)

    def _send_email(self):
        """send the email with the generated pdf to the client and return 1 if
        the email was sent correctly
        """
        msg = EmailMessage(
            subject='Comprovante de pagamento  da reserva',
            body=f'Seu comprovante de pagamento para a reserva do quarto Nº{self.payment.reservation.room.number}',
            to=[self.payment.reservation.client.email],
            from_email=self.hotel_contact.email,
        )
        msg.attach(self.pdf_name, self.buffer.getvalue(), 'application/pdf')
        return msg.send(fail_silently=False)


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
                + timedelta(minutes=ReserveSupport.RESERVATION_PATIENCE_MINUTES)
            ).timestamp()
        )
        self.reservation = reservation

        params = self._create_params()
        self._session = self._create_session(**params)
    
    @property
    def session(self):
        return self._session

    def _create_params(self) -> dict[str, Any]:
        prod_name = f"Reserva: Quarto Nº{self.reservation.room.number}, classe {self.reservation.room.room_class}."
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
                        "unit_amount": self.reservation.room.daily_price_in_cents,
                    },
                    "quantity": self.reservation.reservation_days,
                }
            ],
        }
        return params
    
    def _create_session(self, **params) -> Session:
        return Session.create(**params)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self.__dict__})'


def resize_image(img_path, w, h=None):
    """redimensiona imagem com tamanhos expecificados

    Args:
        img_path (Any): caminho da imagem
        w (int): largura da imagem
        h (int, optional): altura da imagem. Defaults to None.
    """
    img = Image.open(img_path)
    original_w, original_h = img.size

    if h is None: h = round(w * original_h / original_w)
    if original_h <= h: h = original_h
    
    resized = img.resize((w, h), Image.Resampling.NEAREST)
    resized.save(img_path, optimize=True, quality=70)

    resized.close()
    img.close()


def fmt_date(value: str, fmt='%d/%m/%Y') -> str:
    """formata a data no formato especificado.

    Args:
        value (str): data a ser formatada
        fmt (str, optional): padrão para a formatação. Defaults to '%d/%m/%Y'.

    Returns:
        str: data formatada.
    """
    return datetime.strftime(value, fmt)


def verify_captcha(captcha_resp) -> bool:
    """realiza a validação do google recaptcha v3

    Args:
        captcha_resp (Any): resposta do usuário para o captcha

    Returns:
        bool: retorna True se o captcha é valido
    """
    data = {
        'response': captcha_resp,
        'secret': settings.G_RECAPTCHA_KEY_SECRET
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    json_resp = response.json()
    print(json_resp)
    return True if json_resp.get('success', False) else False
