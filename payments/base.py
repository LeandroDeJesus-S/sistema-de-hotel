# from abc import ABC, abstractmethod
# from dataclasses import dataclass
# from typing import Any
#
#
# @dataclass(frozen=True)
# class PaymentSessionResponse:
#     """Standardized response object for payment session creation."""
#
#     redirect_url: str
#     """The URL to which the user should be redirected to complete the payment."""
#
#
# class AbsSessionBasedPayment(ABC):
#     """Abstract Base Class for creating session-based reservation payments."""
#
#     @abstractmethod
#     def __init__(
#         self,
#         request: Any,
#         reservation: Any,
#         success_url_name: str,
#         cancel_url_name: str,
#     ) -> None:
#         """
#         Initializes the payment creator with the necessary context.
#
#         Args:
#             request: The Django HttpRequest object.
#             reservation: The Reservation object.
#             success_url_name: URL name for successful payment redirection.
#             cancel_url_name: URL name for cancelled payment redirection.
#         """
#         pass
#
#     @property
#     @abstractmethod
#     def session(self) -> PaymentSessionResponse:
#         """Returns the created payment session response, including the redirect URL."""
#         pass
