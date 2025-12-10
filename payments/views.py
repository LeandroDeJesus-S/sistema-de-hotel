import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseNotAllowed
from django.http.response import HttpResponse
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
from payments.infra import presenters
from payments.infra.tasks import send_payment_confirmation
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ReleaseReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.decorators import check_reservation_ownership
from reservations.infra.repo import ReservationRepository, RoomRepository
from reservations.infra.tasks import release_reservation_task
from utils.adapters.email import DjangoEmailSender
from utils.adapters.pdf import ReportLabPDFReceiptGenerator
from utils.adapters.queue import DjangoQTaskQueuer
from utils.adapters.unit_of_work import UnitOfWork
from utils.support import captcha_required

from .infra.adapters import (
    CheckoutExpiredEvent,
    CheckoutSessionCreatedEvent,
    CheckoutSucceededEvent,
    StripeCheckoutSession,
    StripePaymentWebhookHandler,
)
from .infra.repo import PaymentRepository

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
@method_decorator(check_reservation_ownership, name='dispatch')
class Checkout(LoginRequiredMixin, View):
    """
    View that renders the checkout page and handles the creation of the payment session.
    """

    login_url = reverse_lazy('signin')
    # template_name = 'checkout.html'

    def get(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):  # noqa: PLR6301
        checkout_res = svc.render_checkout(reservation_pk)
        return presenters.checkout_get_presenter(request, checkout_res).unwrap()

    def post(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):  # noqa: PLR6301
        response = svc.handle_checkout(
            reservation_id=reservation_pk,
            client_id=request.user.pk,
            success_url=request.build_absolute_uri(
                reverse('payment_success', args=[reservation_pk])
            ),
            cancel_url=request.build_absolute_uri(
                reverse('payment_cancel', args=[reservation_pk])
            ),
        )
        return presenters.checkout_post_presenter(request, response).unwrap()


@check_reservation_ownership
@login_required(login_url=reverse_lazy('signin'))
@require_GET
def payment_success(request: HttpRequest, reservation_pk: int):
    """The page where the user is redirected after the payment is successful."""

    result = svc.render_payment_success(reservation_pk)
    return presenters.payment_success_get_presenter(request, result)


@check_reservation_ownership
@login_required(login_url=reverse_lazy('signin'))
@require_GET
def payment_cancel(request: HttpRequest, reservation_pk: int):
    """The page where the user is redirected after the payment is canceled."""
    result = svc.render_payment_cancel(reservation_pk)
    return presenters.payment_cancel_get_presenter(request, result)


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
