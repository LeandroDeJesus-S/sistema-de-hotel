import logging
from typing import Any
from django.http import HttpRequest
from django.views.decorators.http import require_GET
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from reservations.models import Reservation, Room
from reservations.validators import convert_date
from .models import Scheduling
from payments.models import Payment
from django_q.tasks import Schedule, Task, async_task
from payments.tasks import create_payment_pdf
from utils.support import ReservationStripePaymentCreator
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from reservations.mixins import LoginRequired
from reservations.decorators import check_reservation_ownership
from django.contrib import messages
from django.db import OperationalError
from utils.supportviews import CheckoutMessages
from django.db import transaction
from django.core.exceptions import ValidationError
from utils import support


class Schedules(LoginRequired, View):
    """View responsável por gerenciar os dados de agendamentos
    e redirecionar para a página de pagamentos."""
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')
        self.context = {}
    
    def get(self, request, room_pk, *args, **kwargs):
        self.logger.debug(f'schedule for room {room_pk} received')
        self.context['room_pk'] = room_pk
        return render(self.request, 'schedule.html', self.context)

    @transaction.atomic
    def post(self, request, room_pk, *args, **kwargs):
        """valida os dados do formulário de agendamento, inicia a
        reserva, pagamento, cria uma sessão de pagamento e redireciona
        para a pagina hospedada do stripe
        """
        self.logger.debug(f'schedule for room {room_pk} received')
        self.context['room_pk'] = room_pk
        CHECK_IN = convert_date(self.request.POST.get('checkin', '0001-01-01'))
        CHECKOUT = convert_date(self.request.POST.get('checkout', '0001-01-01'))
        OBS = self.request.POST.get('obs', '')
        captcha = request.POST.get('g-recaptcha-response')
        if not support.verify_captcha(captcha):
            messages.error(request, 'Mr. Robot, é você???')
            return redirect(request.META.get('HTTP_REFERER', reverse('schedule', args=(room_pk,))))
        
        try:
            room = get_object_or_404(Room, pk__exact=room_pk)
            reservation = Reservation.objects.filter(
                client=self.request.user,
                checkin=CHECK_IN,
                checkout=CHECKOUT
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

            stripe_payment = ReservationStripePaymentCreator(
                request=self.request,
                reservation=reservation,
                success_url_name='schedule_success',
                cancel_url_name='payment_cancel',
            )
            self.logger.debug(f'stripe payment created {stripe_payment}')

            scheduling = Scheduling(
                client=self.request.user, 
                reservation=reservation
            )
            scheduling.full_clean()
            self.logger.debug(f'schedule {scheduling} prepared')
            payment = Payment(
                status='P',
                amount=reservation.amount,
                reservation=reservation
            )
            payment.full_clean()
            self.logger.debug(f'payment {payment} created')

            scheduling.save()
            payment.save()
            self.logger.debug('models saved')
            return redirect(stripe_payment.session.url)
        
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            self.logger.error(exc.error_dict)
            return render(request, 'schedule.html', self.context)
        
        except OperationalError as exc:
            messages.info(request, CheckoutMessages.TRANSACTION_BLOCKING)
            self.logger.warn(f"payment transaction fail: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("rooms"))
            return redirect(redirect_url)

        except Exception as exc:
            messages.error(request, CheckoutMessages.PAYMENT_FAIL)
            self.logger.critical(f"payment unexpected fail: {str(exc)}")
            redirect_url = request.META.get("HTTP_REFERER", reverse("rooms"))
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

    schedule = get_object_or_404(Scheduling, client=request.user, reservation=payment.reservation)
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

    task_name = f"create_payment_pdf_{payment.pk}"
    if not Task.objects.filter(name=task_name).exists():
        async_task(create_payment_pdf, payment, task_name=task_name)
        logger.info(f'task {task_name} created')

    logger.debug('rendering schedule_success.html')
    return render(request, 'schedule_success.html', context)
