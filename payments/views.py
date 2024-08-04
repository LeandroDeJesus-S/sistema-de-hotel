import logging

from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_GET
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from reservations.models import Reservation
from utils.supportviews import CheckoutMessages, PaymentCancelMessages
from django.contrib import messages
from .models import Payment
from django.db import transaction
from sqlite3 import OperationalError
from .tasks import create_payment_pdf
from utils.support import ReservationStripePaymentCreator
from django_q.tasks import async_task, Task
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from reservations.decorators import check_reservation_ownership


class Checkout(LoginRequiredMixin, View):
    """view que renderiza a pagina de checkout para o usuário e
    cria a sessão de pagamento do stripe"""
    login_url = reverse_lazy("signin")

    def setup(self, request: HttpRequest, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger("djangoLogger")
        self.template = "checkout.html"

    def get(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        reservation = get_object_or_404(Reservation, pk__exact=reservation_pk)
        self.logger.debug(f"rendering {self.template}")
        return render(request, self.template, {"reservation": reservation})

    @transaction.atomic
    def post(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        try:
            reservation = get_object_or_404(Reservation, pk=reservation_pk)
            reservation_payment = ReservationStripePaymentCreator(
                request=request, 
                reservation=reservation, 
                success_url_name='payment_success',
                cancel_url_name='payment_cancel'
            )

            self.logger.debug(f"success callback url: {reservation_payment.success_url}")
            self.logger.debug(f"cancel callback url: {reservation_payment.cancel_url}")

            reservation._validate_room()

            reservation.room.available = False
            reservation.status = "P"

            payment = Payment(
                reservation=reservation, amount=reservation.amount, status="P"
            )
            payment.full_clean()

            reservation.room.save()
            reservation.save()
            payment.save()
            self.logger.info(f'payment {payment.pk} created for reservation {reservation.pk}')
            return redirect(reservation_payment.session.url)

        except OperationalError as exc:
            messages.info(request, CheckoutMessages.TRANSACTION_BLOCKING)
            self.logger.critical(f"payment transaction fail: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("rooms"))
            return redirect(redirect_url)

        except Exception as exc:
            messages.error(request, CheckoutMessages.PAYMENT_FAIL)
            self.logger.critical(f"payment unexpected fail: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("rooms"))
            return redirect(redirect_url)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=kwargs.get("reservation_pk"))
        if request.user.is_authenticated and reservation.client != request.user:
            self.logger.warn(
                f'permission denied for user {request.user.pk} to access reservation {reservation.pk}'
            )
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


@require_GET
@login_required(login_url=reverse_lazy("signin"))
@check_reservation_ownership
def payment_success(request: HttpRequest, reservation_pk: int):
    """renderiza a página de sucesso do pagamento, finaliza e ativa a reserva,
    e cria um task que envia os dados de pagamento por email para o cliente"""    
    logger = logging.getLogger("djangoLogger")
    logger.info(f"reserva {reservation_pk} recebida para sucesso de pagamento")

    payment = get_object_or_404(Payment, reservation__pk=reservation_pk)
    if payment.status == "P":
        payment.reservation.status = "A"
        payment.reservation.active = True
        payment.reservation.save()

        payment.status = "F"
        payment.save()

    task_name = f"create_payment_pdf_{payment.pk}"
    if not Task.objects.filter(name=task_name).exists():
        logger.info(f'task {task_name} created')
        async_task(create_payment_pdf, payment, task_name=task_name)

    logger.debug(f"rendering success page for payment: {payment.pk}")
    return render(request, "success.html", {"payment": payment})


@require_GET
@login_required(login_url=reverse_lazy("signin"))
@check_reservation_ownership
def payment_cancel(request: HttpRequest, reservation_pk: int):
    """renderia a página de cancelamento do pagamento, coloca o status
    do pagamento para cancelado e libera o quarto"""
    logger = logging.getLogger("djangoLogger")
    logger.info(f"reservation {reservation_pk} received to cancel")
    try:
        payment = get_object_or_404(Payment, reservation__pk=reservation_pk)
        if payment.status != "C":
            payment.reservation.status = "C"
            payment.reservation.active = False
            payment.reservation.room.available = True
            payment.reservation.room.save()
            payment.reservation.save()
            payment.reservation.save()

            payment.status = "C"
            payment.save()
            logger.info(f"payment {payment.pk} for {payment.reservation.pk} successfully canceled")
    
    except Exception as exc:
        logger.critical(
            f"unexpected error reverting reservation {reservation_pk}: {str(exc)}"
        )
        messages.error(request, PaymentCancelMessages.UNEXPECTED_ERROR)
        return redirect('rooms')

    return render(request, "cancel.html")
