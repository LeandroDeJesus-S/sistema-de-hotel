import logging
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET
from django_q.tasks import Schedule, Task, async_task

from payments.error_messages import CheckoutMessages
from payments.models import Payment
from payments.stripe_payment import ReservationSessionBasedPaymentCreator
from payments.tasks import create_payment_pdf
from reservations.decorators import check_reservation_ownership
from reservations.mixins import LoginRequired
from reservations.models import Reservation, Room
from reservations.validators import convert_date
from utils import support

from .models import Scheduling

CAPTCHA_CTX = {'recaptcha_site_key': settings.G_RECAPTCHA_KEY_SITE}


@method_decorator(support.captcha_required('schedule', params=('room_pk',)), name='post')
class Schedules(LoginRequired, View):
    """View responsável por gerenciar os dados de agendamentos
    e redirecionar para a página de pagamentos."""

    payment_creator_cls = ReservationSessionBasedPaymentCreator

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.context: dict[str, Any] = {}

    def get(self, request, room_pk, *args, **kwargs):
        self.logger.debug(f'schedule for room {room_pk} received')
        self.context['room_pk'] = room_pk
        return render(self.request, 'schedule.html', {**self.context, **CAPTCHA_CTX})

    @transaction.atomic
    def post(self, request, room_pk, *args, **kwargs):  # noqa: PLR0915
        """valida os dados do formulário de agendamento, inicia a
        reserva, pagamento, cria uma sessão de pagamento e redireciona
        para a pagina hospedada do stripe
        """
        self.logger.debug(f'schedule for room {room_pk} received')
        self.context['room_pk'] = room_pk
        check_in_result = convert_date(self.request.POST.get('checkin', '0001-01-01'))
        checkout_result = convert_date(self.request.POST.get('checkout', '0001-01-01'))

        if check_in_result.is_err() or checkout_result.is_err():
            err = (
                check_in_result.unwrap_err()
                if check_in_result.is_err()
                else checkout_result.unwrap_err()
            )
            messages.error(request, err.msg)
            self.logger.error(err.msg, exc_info=err.src_error)
            return render(request, 'schedule.html', {**self.context, **CAPTCHA_CTX})

        CHECK_IN = check_in_result.unwrap()
        CHECKOUT = checkout_result.unwrap()
        OBS = self.request.POST.get('obs', '')

        try:
            room = get_object_or_404(Room, pk__exact=room_pk)
            reservation = Reservation.objects.filter(
                client=self.request.user, checkin=CHECK_IN, checkout=CHECKOUT
            ).first()
            self.logger.debug(f'existing reservation {reservation}')

            if reservation is None:
                self.logger.debug('creating a new reservation')
                reservation = Reservation(
                    checkin=CHECK_IN,
                    checkout=CHECKOUT,
                    observations=OBS,
                    client=self.request.user,
                    room=room,
                )
                reservation.amount = reservation.calc_reservation_value()

                reservation.error_messages = {}
                reservation._validate_date_availability(reservation.error_messages, 'checkin')
                reservation._validate_check_in()
                if reservation.error_messages:
                    self.logger.error(str(reservation.error_messages))
                    raise ValidationError(reservation.error_messages)

                reservation.clean_fields()
                reservation.save()
                self.logger.info(f'reservation {reservation.pk} created')

            stripe_payment = self.payment_creator_cls(
                request=self.request,
                reservation=reservation,
                success_url_name='schedule_success',
                cancel_url_name='payment_cancel',
            )
            self.logger.debug(f'stripe payment created {stripe_payment}')

            scheduling = Scheduling(client=self.request.user, reservation=reservation)
            scheduling.full_clean()
            self.logger.debug(f'schedule {scheduling} prepared')

            payment = Payment(status='P', amount=reservation.amount, reservation=reservation)
            payment.full_clean()
            self.logger.debug(f'payment {payment} created')

            scheduling.save()
            payment.save()
            self.logger.debug('models saved')
            return redirect(stripe_payment.session.redirect_url)

        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            self.logger.error(exc.error_dict)
            return render(request, 'schedule.html', {**self.context, **CAPTCHA_CTX})

        except OperationalError as exc:
            messages.info(request, CheckoutMessages.TRANSACTION_BLOCKING)
            self.logger.warning(f'payment transaction fail: {str(exc)}')
            redirect_url = request.META.get('HTTP_REFERER', reverse('rooms'))
            return redirect(redirect_url)

        except Exception as exc:
            messages.error(request, CheckoutMessages.PAYMENT_FAIL)
            self.logger.critical(f'payment unexpected fail: {str(exc)}')
            redirect_url = request.META.get('HTTP_REFERER', reverse('rooms'))
            return redirect(redirect_url)


@require_GET
@login_required(login_url=reverse_lazy('signin'))
@check_reservation_ownership
def schedule_success(request: HttpRequest, reservation_pk: int):
    """view responsável de renderizar a pagina de sucesso do pagamento
    da reserva e criar uma task para enviar os dados de pagamento via
    email para o cliente.
    """
    logger = logging.getLogger('djangoLogger')

    payment = get_object_or_404(Payment, reservation__pk__exact=reservation_pk)
    context = {'payment': payment}
    if not payment.status == 'P':
        logger.warn('payment is not processing')
        return render(request, 'schedule_success.html', context)

    payment.reservation.status = 'S'
    payment.status = 'F'
    payment.reservation.save()
    payment.save()
    context['payment'] = payment
    logger.info(f'payment {payment} created')

    schedule = get_object_or_404(
        Scheduling, client=request.user, reservation=payment.reservation
    )
    schedule_name = f'schedule {schedule}-{schedule.client}-{schedule.reservation}'
    if not Schedule.objects.filter(name=schedule_name).exists():
        Schedule.objects.create(
            func='schedules.tasks.schedule_reservation',
            args=str(schedule.reservation.pk),
            next_run=payment.reservation.checkin,
            repeats=1,
            name=schedule_name,
        )
        logger.info(f'schedule {schedule_name} created')

    task_name = f'create_payment_pdf_{payment.pk}'
    if not Task.objects.filter(name=task_name).exists():
        async_task(create_payment_pdf, payment, task_name=task_name)
        logger.info(f'task {task_name} created')

    logger.debug('rendering schedule_success.html')
    return render(request, 'schedule_success.html', context)
