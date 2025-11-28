import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseNotAllowed
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from clients.infra.repo import ClientRepository
from payments.application.services import PaymentService
from payments.application.usecases import (
    SendPaymentConfirmationUseCase,
)
from payments.infra.tasks import send_payment_confirmation
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.decorators import check_reservation_ownership
from reservations.infra.repo import ReservationRepository, RoomRepository
from reservations.infra.tasks import release_reservation_task
from reservations.models import Reservation
from utils.adapters.email import DjangoEmailSender
from utils.adapters.pdf import ReportLabPDFReceiptGenerator
from utils.adapters.queue import DjangoQTaskQueuer
from utils.adapters.unit_of_work import UnitOfWork
from utils.support import captcha_required

from .error_messages import CheckoutMessages
from .infra.adapters import (
    CheckoutExpiredEvent,
    CheckoutSessionCreatedEvent,
    CheckoutSucceededEvent,
    StripeCheckoutSession,
    StripePaymentWebhookHandler,
)
from .infra.repo import PaymentRepository
from .models import Payment

RECAPTCHA_CTX = {'recaptcha_site_key': settings.G_RECAPTCHA_KEY_SITE}
uow = UnitOfWork()
payment_repo = PaymentRepository()
reservation_repo = ReservationRepository()
room_repo = RoomRepository()
task_queuer = DjangoQTaskQueuer()
mailer = DjangoEmailSender()
pdf_generator = ReportLabPDFReceiptGenerator()
confirmation_usecase = SendPaymentConfirmationUseCase(mailer, pdf_generator)
activate_reservatoin_usecase = ActivateReservationUseCase(reservation_repo, room_repo, uow)
schedule_reservation_usecase = ScheduleReservationUseCase(
    reservation_repo,
    uow,
    task_queuer,
)
release_reservation_usecase = ReleaseReservationUseCase(
    room_repo, reservation_repo, payment_repo, uow
)
payment_gateway = StripeCheckoutSession(settings.STRIPE_API_KEY_SECRET)
svc = PaymentService(
    payment_gateway=payment_gateway,
    payment_repo=payment_repo,
    uow=uow,
    logger=logging.getLogger('djangoLogger'),
    reservation_repo=reservation_repo,
    client_repo=ClientRepository(),
    wh_handler=StripePaymentWebhookHandler(),
)


@method_decorator(captcha_required('rooms'), name='post')
class Checkout(LoginRequiredMixin, View):
    """
    View that renders the checkout page and handles the creation of the payment session.
    """

    login_url = reverse_lazy('signin')
    template_name = 'checkout.html'

    def setup(self, request: HttpRequest, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.logger = logging.getLogger('djangoLogger')

    def get(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        reservation = reservation_repo.find_by_id(reservation_pk)
        if reservation.is_err():
            messages.error(request, 'invalid operation')
            return redirect(reverse('rooms'))

        reservation = reservation.unwrap()
        self.logger.debug(f'Rendering {self.template_name}')
        return render(
            request, self.template_name, {'reservation': reservation, **RECAPTCHA_CTX}
        )

    def post(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        def _on_err(err):
            messages.error(request, CheckoutMessages.PAYMENT_FAIL)
            self.logger.critical(
                'Checkout use case failed: %s', str(err), exc_info=err.src_error
            )
            return redirect(request.META.get('HTTP_REFERER', reverse('rooms')))

        def _on_ok(result):
            return redirect(result.session_url)

        response = svc.start_checkout(
            reservation_id=reservation_pk,
            client_id=request.user.pk,
            success_url=request.build_absolute_uri(
                reverse('payment_success', args=[reservation_pk])
            ),
            cancel_url=request.build_absolute_uri(
                reverse('payment_cancel', args=[reservation_pk])
            ),
        ).match(
            on_err=_on_err,
            on_ok=_on_ok,
        )
        return response

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=kwargs.get('reservation_pk'))
        if request.user.is_authenticated and reservation.client != request.user:
            self.logger.warning(
                f'permission denied for user {request.user.pk} '
                f'to access reservation {reservation.pk}'
            )
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


@require_GET
@login_required(login_url=reverse_lazy('signin'))
@check_reservation_ownership
def payment_success(request: HttpRequest, reservation_pk: int):
    """renderiza a página de sucesso do pagamento, finaliza e ativa a reserva,
    e cria um task que envia os dados de pagamento por email para o cliente"""
    logger = logging.getLogger('djangoLogger')
    logger.info(f'reserva {reservation_pk} recebida para sucesso de pagamento')

    payment = get_object_or_404(
        Payment, reservation__client=request.user, reservation__pk=reservation_pk
    )
    logger.debug(f'rendering success page for payment: {payment.pk}')
    return render(request, 'success.html', {'payment': payment})


@require_GET
@login_required(login_url=reverse_lazy('signin'))
@check_reservation_ownership
def payment_cancel(request: HttpRequest, reservation_pk: int):
    """renderia a página de cancelamento do pagamento, coloca o status
    do pagamento para cancelado e libera o quarto"""
    logger = logging.getLogger('djangoLogger')
    logger.info(f'reservation {reservation_pk} received to cancel')
    return render(request, 'cancel.html')


@csrf_exempt
def stripe_webhook(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    result = svc.handle_webhook(
        {
            'request_body': request.body,
            'stripe_signature_header': request.headers.get('stripe-signature'),
        },
        CheckoutSucceededEvent(
            task_queuer,
            payment_repo,
            send_payment_confirmation,
            activate_reservatoin_usecase,
            release_reservation_task,
            schedule_reservation_usecase,
        ),
        CheckoutExpiredEvent(payment_repo, reservation_repo),
        CheckoutSessionCreatedEvent(),
    ).unwrap()  # XXX: unwrap is safe here, since it never returns an error

    return HttpResponse(
        status=result.response_code, content=(result.err_msg or '').encode('utf-8')
    )
