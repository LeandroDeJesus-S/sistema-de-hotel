import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from reservations.models import Reservation
from utils.supportviews import PaymentMessages
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
        self.logger.debug("renderizando checkout.html")
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
            return redirect(reservation_payment.session.url)

        except OperationalError as exc:
            messages.info(request, PaymentMessages.TRANSACTION_BLOCKING)
            self.logger.critical(f"Falha na criação do pagamento: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("rooms"))
            return redirect(redirect_url)

        except Exception as exc:
            messages.error(request, PaymentMessages.PAYMENT_FAIL)
            self.logger.critical(f"Falha na criação do pagamento: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("rooms"))
            return redirect(redirect_url)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=kwargs.get("reservation_pk"))
        if reservation.client != request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


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
        async_task(create_payment_pdf, payment, task_name=task_name)

    logger.debug(f"renderizando pagina de sucesso com pagamento: {payment}")
    return render(request, "success.html", {"payment": payment})


@login_required(login_url=reverse_lazy("signin"))
@check_reservation_ownership
def payment_cancel(request: HttpRequest, reservation_pk: int):
    """renderia a página de cancelamento do pagamento, coloca o status
    do pagamento para cancelado e libera o quarto"""
    logger = logging.getLogger("djangoLogger")
    logger.info(f"reserva {reservation_pk} recebida para cancelamento")
    try:
        payment = Payment.objects.get(reservation__pk=reservation_pk)
        if payment.status != "C":
            payment.reservation.status = "C"
            payment.reservation.active = False
            payment.reservation.room.available = True
            payment.reservation.room.save()
            payment.reservation.save()
            payment.reservation.save()

            payment.status = "C"
            payment.save()

    except Exception as e:
        logger.critical(
            f"nao foi possivel reverter o pagamento {payment} para a reserva {payment.reservation} : {str(e)}"
        )

    logger.info(f"pagamento {payment} para a reserva {payment.reservation} cancelado")
    return render(request, "cancel.html")
