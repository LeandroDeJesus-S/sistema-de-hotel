from typing import Any, Callable

from dependency_injector.wiring import Provide, inject
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseNotAllowed
from django.http.response import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from base.ports.queue import TaskQueuer
from base.ports.unit_of_work import AbsUnitOfWork
from payments.application.services import PaymentService
from payments.container import PaymentsContainer
from payments.domain.ports import AbsPaymentsRepository
from payments.infra import presenters
from reservations.application.usecases import (
    ActivateReservationUseCase,
    ScheduleReservationUseCase,
)
from reservations.decorators import check_reservation_ownership
from reservations.domain.repo import AbsReservationRepository
from reservations.infra.tasks import release_reservation_task
from utils.support import captcha_required

from .infra.adapters import (
    CheckoutExpiredEvent,
    CheckoutSucceededEvent,
)


@method_decorator(captcha_required('rooms'), name='post')
@method_decorator(check_reservation_ownership, name='dispatch')
class Checkout(LoginRequiredMixin, View):
    """
    View that renders the checkout page and handles the creation of the payment session.
    """

    login_url = reverse_lazy('signin')
    # template_name = 'checkout.html'

    @inject
    def get(
        self,
        request: HttpRequest,
        reservation_pk: int,
        *args,
        svc: PaymentService = Provide[PaymentsContainer.payment_service],
        **kwargs,
    ):  # noqa: PLR6301
        checkout_res = svc.render_checkout(reservation_pk)
        return presenters.checkout_get_presenter(request, checkout_res).unwrap()

    @inject
    def post(
        self,
        request: HttpRequest,
        reservation_pk: int,
        *args,
        svc: PaymentService = Provide[PaymentsContainer.payment_service],
        **kwargs,
    ):  # noqa: PLR6301
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
@inject
def payment_success(
    request: HttpRequest,
    reservation_pk: int,
    svc: PaymentService = Provide[PaymentsContainer.payment_service],
):
    """The page where the user is redirected after the payment is successful."""

    result = svc.render_payment_success(reservation_pk)
    return presenters.payment_success_get_presenter(request, result)


@check_reservation_ownership
@login_required(login_url=reverse_lazy('signin'))
@require_GET
@inject
def payment_cancel(
    request: HttpRequest,
    reservation_pk: int,
    svc: PaymentService = Provide[PaymentsContainer.payment_service],
):
    """The page where the user is redirected after the payment is canceled."""
    result = svc.render_payment_cancel(reservation_pk)
    return presenters.payment_cancel_get_presenter(request, result)


@csrf_exempt
@inject
def stripe_webhook(  # noqa: PLR0913, PLR0917
    request: HttpRequest,
    task_queuer: TaskQueuer = Provide[PaymentsContainer.task_queuer],
    payment_repo: AbsPaymentsRepository = Provide[PaymentsContainer.payment_repo],
    reservation_repo: AbsReservationRepository = Provide[PaymentsContainer.reservation_repo],
    send_payment_confirmation: Callable[..., Any] = Provide[
        PaymentsContainer.confirmation_usecase
    ],
    activate_reservation_usecase: ActivateReservationUseCase = Provide[
        PaymentsContainer.activate_reservation_usecase
    ],
    schedule_reservation_usecase: ScheduleReservationUseCase = Provide[
        PaymentsContainer.schedule_reservation_usecase
    ],
    svc: PaymentService = Provide[PaymentsContainer.payment_service],
    uow: AbsUnitOfWork = Provide[PaymentsContainer.unit_of_work],
):
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
            activate_reservation_usecase,
            release_reservation_task,
            schedule_reservation_usecase,
            uow,
        ),
        CheckoutExpiredEvent(payment_repo, reservation_repo),
    ).unwrap()  # XXX: unwrap is safe here, since it never returns an error

    return HttpResponse(
        status=result.response_code, content=(result.err_msg or '').encode('utf-8')
    )
