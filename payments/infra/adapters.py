from typing import Any

import stripe

from exc import Result
from payments.domain.dtos import CheckoutResultDTO, CheckoutSessionInputDTO
from payments.domain.ports import AbsSessionBasedPayment


class StripeCheckoutSession(AbsSessionBasedPayment):
    def __init__(self, stripe_api_key: str):
        self._stripe_api_key = stripe_api_key

    def create_checkout_session(
        self, dto: CheckoutSessionInputDTO
    ) -> Result[CheckoutResultDTO]:
        if len(dto.items) <= 0:
            return Result.Err('No items provided')

        try:
            params: dict[str, Any] = {
                'mode': 'payment',
                'success_url': dto.success_url,
                'cancel_url': dto.return_url,
                'expires_at': int(dto.expires_at.timestamp()),
                'line_items': [
                    {
                        'price_data': {
                            'currency': dto.currency,
                            'product_data': {
                                'name': item.name,
                                'description': item.description,
                            },
                            'unit_amount': item.unit_price_cents,
                        },
                        'quantity': item.quantity,
                    }
                    for item in dto.items
                ],
            }

            session = stripe.checkout.Session.create(**params, api_key=self._stripe_api_key)
            result = CheckoutResultDTO(session_id=session.id, session_url=session.url or '')
            return Result.Ok(result)

        except Exception as e:
            return Result.Err('Failed to create Stripe session', src_error=e)
