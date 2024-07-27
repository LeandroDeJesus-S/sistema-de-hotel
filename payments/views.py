import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from reservas.models import Reserva
from utils.supportviews import PaymentMessages
from django.contrib import messages
from .models import Pagamento
from django.db import transaction
from sqlite3 import OperationalError
from .tasks import create_payment_pdf
from utils.support import ReservationStripePaymentCreator
from django_q.tasks import async_task, Task
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from reservas.decorators import check_reservation_ownership


class Payment(LoginRequiredMixin, View):
    login_url = reverse_lazy("signin")

    def setup(self, request: HttpRequest, *args, **kwargs) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger("djangoLogger")
        self.template = "checkout.html"

    def get(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        reservation = get_object_or_404(Reserva, pk__exact=reservation_pk)
        self.logger.debug("renderizando checkout.html")
        return render(request, self.template, {"reservation": reservation})

    @transaction.atomic
    def post(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        try:
            reservation = get_object_or_404(Reserva, pk=reservation_pk)
            reservation_payment = ReservationStripePaymentCreator(
                request=request, 
                reservation=reservation, 
                success_url_name='payment_success',
                cancel_url_name='payment_cancel'
            )

            self.logger.debug(f"success callback url: {reservation_payment.success_url}")
            self.logger.debug(f"cancel callback url: {reservation_payment.cancel_url}")

            reservation._validate_room()

            reservation.quarto.disponivel = False
            reservation.status = "P"

            payment = Pagamento(
                reserva=reservation, valor=reservation.custo, status="p"
            )
            payment.full_clean()

            reservation.quarto.save()
            reservation.save()
            payment.save()
            return redirect(reservation_payment.session.url)

        except OperationalError as exc:
            messages.info(request, PaymentMessages.TRANSACTION_BLOCKING)
            self.logger.critical(f"Falha na criação do pagamento: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("quartos"))
            return redirect(redirect_url)

        except Exception as exc:
            messages.error(request, PaymentMessages.PAYMENT_FAIL)
            self.logger.critical(f"Falha na criação do pagamento: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("quartos"))
            return redirect(redirect_url)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        reservation = get_object_or_404(Reserva, pk=kwargs.get("reservation_pk"))
        if reservation.cliente != request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


@login_required(login_url=reverse_lazy("signin"))
@check_reservation_ownership
def payment_success(request: HttpRequest, reservation_pk: int):
    logger = logging.getLogger("djangoLogger")
    logger.info(f"reserva {reservation_pk} recebida para sucesso de pagamento")

    payment = get_object_or_404(Pagamento, reserva__pk=reservation_pk)
    if payment.status == "p":
        payment.reserva.status = "A"
        payment.reserva.ativa = True
        payment.reserva.save()

        payment.status = "f"
        payment.save()

    task_name = f"create_payment_pdf_{payment.pk}"
    if not Task.objects.filter(name=task_name).exists():
        async_task(create_payment_pdf, payment, task_name=task_name)

    logger.debug(f"renderizando pagina de sucesso com pagamento: {payment}")
    return render(request, "success.html", {"payment": payment})


@login_required(login_url=reverse_lazy("signin"))
@check_reservation_ownership
def payment_cancel(request: HttpRequest, reservation_pk: int):
    logger = logging.getLogger("djangoLogger")
    logger.info(f"reserva {reservation_pk} recebida para cancelamento")
    try:
        payment = Pagamento.objects.get(reserva__pk=reservation_pk)
        if payment.status != "c":
            payment.reserva.status = "C"
            payment.reserva.ativa = False
            payment.reserva.quarto.disponivel = True
            payment.reserva.quarto.save()
            payment.reserva.save()
            payment.reserva.save()

            payment.status = "c"
            payment.save()

    except Exception as e:
        logger.critical(
            f"nao foi possivel reverter o pagamento {payment} para a reserva {payment.reserva} : {str(e)}"
        )

    logger.info(f"pagamento {payment} para a reserva {payment.reserva} cancelado")
    return render(request, "cancel.html")
