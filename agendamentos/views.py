import logging
from typing import Any
from django.http import HttpRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from reservas.models import Reserva, Quarto
from reservas.validators import convert_date
from .models import Agendamento
from payments.models import Pagamento
from django_q.tasks import Schedule, Task, async_task
from payments.tasks import create_payment_pdf
from utils.support import ReservationStripePaymentCreator
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from reservas.mixins import LoginRequired
from reservas.decorators import check_reservation_ownership
from django.contrib import messages
from sqlite3 import OperationalError
from utils.supportviews import PaymentMessages
from django.db import transaction
from django.core.exceptions import ValidationError


class Agendar(LoginRequired, View):  # TODO: criar testes
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.context = {}
    
    def get(self, request, quarto_pk, *args, **kwargs):
        self.context['quarto_pk'] = quarto_pk
        return render(self.request, 'agendamentos.html', self.context)

    @transaction.atomic
    def post(self, request, quarto_pk, *args, **kwargs):
        self.context['quarto_pk'] = quarto_pk
        CHECK_IN = convert_date(self.request.POST.get('checkin', '0001-01-01'))
        CHECKOUT = convert_date(self.request.POST.get('checkout', '0001-01-01'))
        OBS = self.request.POST.get('obs', '')
        
        try:
            reservation_exists = Reserva.objects.filter(
                cliente=self.request.user,
                check_in=CHECK_IN,
                checkout=CHECKOUT
            ).exists()
            if not reservation_exists:
                reserva = Reserva(
                    check_in=CHECK_IN, 
                    checkout=CHECKOUT,
                    observacoes=OBS,
                    cliente=self.request.user,
                    quarto=get_object_or_404(Quarto, pk__exact=quarto_pk),
                )
                reserva.custo = reserva.calc_reservation_value()

                reserva.error_messages = {}
                reserva._validate_check_in()
                if reserva.error_messages:
                    raise ValidationError(reserva.error_messages)
                
                reserva.clean_fields()
                reserva.save()

            stripe_payment = ReservationStripePaymentCreator(
                request=self.request,
                reservation=reserva,
                success_url_name='agendamento_success',
                cancel_url_name='payment_cancel',
            )

            agendamento = Agendamento(
                cliente=self.request.user, 
                reserva=reserva
            )
            agendamento.full_clean()

            payment = Pagamento(
                status='p',
                valor=reserva.custo,
                reserva=reserva
            )
            payment.full_clean()
            
            agendamento.save()
            payment.save()
            return redirect(stripe_payment.session.url)
        
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            self.logger.error(exc.error_dict)
            return render(request, 'agendamentos.html', self.context)
        
        except OperationalError as exc:
            messages.info(request, PaymentMessages.TRANSACTION_BLOCKING)
            self.logger.warn(f"Falha na criação do pagamento: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("quartos"))
            return redirect(redirect_url)

        except Exception as exc:
            messages.error(request, PaymentMessages.PAYMENT_FAIL)
            self.logger.critical(f"Falha na criação do pagamento: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("quartos"))
            return redirect(redirect_url)


@login_required(login_url=reverse_lazy('signin'))
@check_reservation_ownership
def agendamento_success(request: HttpRequest, reservation_pk: int):
    payment = get_object_or_404(Pagamento, reserva__pk__exact=reservation_pk)
    context = {'payment': payment}
    if not payment.status == 'p':
        return render(request, 'agendamento_success.html', context)
    
    payment.reserva.status = 'S'
    payment.status = 'f'
    payment.reserva.save()
    payment.save()
    context['payment'] = payment
    
    agendamento = get_object_or_404(Agendamento, cliente=request.user, reserva=payment.reserva)
    schedule_name = f'agendamento {agendamento}-{agendamento.cliente}-{agendamento.reserva}'
    if not Schedule.objects.filter(name=schedule_name).exists():
        Schedule.objects.create(
            func='agendamentos.tasks.schedule_reservation',
            args=str(agendamento.reserva.pk),
            next_run=payment.reserva.check_in,
            repeats=1,
            name=schedule_name,
        )

    task_name = f"create_payment_pdf_{payment.pk}"
    if not Task.objects.filter(name=task_name).exists():
        async_task(create_payment_pdf, payment, task_name=task_name)

    return render(request, 'agendamento_success.html', context)
