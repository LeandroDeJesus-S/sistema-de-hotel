from datetime import timedelta
from typing import Any

import stripe
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from stripe.checkout import Session

from payments.base import AbsSessionBasedPayment, PaymentSessionResponse
from reservations.rules import ReserveSupport


class ReservationSessionBasedPaymentCreator(AbsSessionBasedPayment):
    """Cria a session para pagamento da reserva pelo stripe"""

    stripe.api_key = settings.STRIPE_API_KEY_SECRET

    def __init__(self, request, reservation, success_url_name, cancel_url_name) -> None:
        self.baseurl = f'http://{request.get_host()}'
        self.success_url = self.baseurl + reverse(success_url_name, args=(reservation.pk,))
        self.cancel_url = self.baseurl + reverse(cancel_url_name, args=(reservation.pk,))
        self.expires_at = int(
            (
                now() + timedelta(minutes=ReserveSupport.RESERVATION_PATIENCE_MINUTES)
            ).timestamp()
        )
        self.reservation = reservation

        params = self._create_params()
        self._session = self._create_session(**params)

    @property
    def session(self) -> PaymentSessionResponse:
        if self._session.url is None:
            raise ValueError('Session URL is None')

        return PaymentSessionResponse(redirect_url=self._session.url)

    def _create_params(self) -> dict[str, Any]:
        prod_name = (
            f'Reserva: Quarto Nº{self.reservation.room.number}, '
            f'classe {self.reservation.room.room_class}.'
        )
        params = {
            'mode': 'payment',
            'success_url': self.success_url,
            'cancel_url': self.cancel_url,
            'expires_at': self.expires_at,
            'line_items': [
                {
                    'adjustable_quantity': {
                        'enabled': False,
                    },
                    'price_data': {
                        'currency': 'brl',
                        'product_data': {
                            'name': prod_name,
                        },
                        'unit_amount': self.reservation.room.daily_price_in_cents,
                    },
                    'quantity': self.reservation.reservation_days,
                }
            ],
        }
        return params

    def _create_session(self, **params) -> Session:  # noqa: PLR6301
        return Session.create(**params)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self.__dict__})'
