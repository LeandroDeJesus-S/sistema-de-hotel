import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET
from django_q.tasks import Task, async_task

from clients.infra.repo import ClientRepository
from payments.application.services import PaymentService
from reservations.decorators import check_reservation_ownership
from reservations.infra.repo import ReservationRepository
from reservations.models import Reservation
from utils.adapters.unit_of_work import UnitOfWork
from utils.support import captcha_required

from .error_messages import CheckoutMessages, PaymentCancelMessages
from .infra.adapters import StripeCheckoutSession
from .infra.repo import PaymentRepository
from .models import Payment
from .tasks import create_payment_pdf

RECAPTCHA_CTX = {'recaptcha_site_key': settings.G_RECAPTCHA_KEY_SITE}
svc = PaymentService(
    payment_gateway=StripeCheckoutSession(settings.STRIPE_API_KEY_SECRET),
    payment_repo=PaymentRepository(),
    uow=UnitOfWork(),
    logger=logging.getLogger('djangoLogger'),
    reservation_repo=ReservationRepository(),
    client_repo=ClientRepository(),
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
        reservation = get_object_or_404(Reservation, pk__exact=reservation_pk)
        self.logger.debug(f'Rendering {self.template_name}')
        return render(
            request, self.template_name, {'reservation': reservation, **RECAPTCHA_CTX}
        )

    def post(self, request: HttpRequest, reservation_pk: int, *args, **kwargs):
        def _on_err(err):
            messages.error(request, CheckoutMessages.PAYMENT_FAIL)
            self.logger.critical('Checkout use case failed', exc_info=err.src_error)
            return redirect(request.META.get('HTTP_REFERER', reverse('rooms')))

        def _on_ok(result):
            return redirect(result.redirect_url)

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
        # reservation_model = get_object_or_404(Reservation, pk=reservation_pk)
        #
        # # Convert Django model to domain entity
        # reservation_entity_result = model_to_entity(
        #     reservation_model, self.reservation_repo.entity
        # )
        # if reservation_entity_result.is_err():
        #     messages.error(request, CheckoutMessages.PAYMENT_FAIL)
        #     self.logger.critical(
        #         'Failed to convert reservation model to entity',
        #         exc_info=reservation_entity_result.unwrap_err().src_error,
        #     )
        #     return redirect(request.META.get('HTTP_REFERER', reverse('rooms')))
        #
        # reservation_entity = reservation_entity_result.unwrap()
        #
        # # Prepare DTO for the use case
        # success_url = request.build_absolute_uri(
        #     reverse('payment_success', args=[reservation_pk])
        # )
        # cancel_url = request.build_absolute_uri(
        #     reverse('payment_cancel', args=[reservation_pk])
        # )
        # checkout_dto = CheckoutDTO(
        #     reservation=reservation_entity,
        #     success_url=success_url,
        #     cancel_url=cancel_url,
        # )
        #
        # # Execute the use case
        # result = self.use_case.execute(checkout_dto)
        #
        # if result.is_err():
        #     messages.error(request, CheckoutMessages.PAYIMENT_FAIL)
        #     self.logger.critical(
        #         'Checkout use case failed', exc_info=result.unwrap_err().src_error
        #     )
        #     return redirect(request.META.get('HTTP_REFERER', reverse('rooms')))
        #
        # redirect_url = result.unwrap().redirect_url
        # return redirect(redirect_url)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=kwargs.get('reservation_pk'))
        if request.user.is_authenticated and reservation.client != request.user:
            self.logger.warning(
                f'permission denied for user {request.user.pk} '
                f'to access reservation {reservation.pk}'
            )
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


# TODO: use cases needed
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
    if payment.status == Payment.Status.PENDING:
        payment.reservation.status = Reservation.Status.ACTIVE
        payment.reservation.active = True
        payment.reservation.save()

        payment.status = Payment.Status.COMPLETED
        payment.save()

    task_name = f'create_payment_pdf_{payment.pk}'
    if not Task.objects.filter(name=task_name).exists():
        logger.info(f'task {task_name} created')
        async_task(create_payment_pdf, payment, task_name=task_name)

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
    try:
        payment = get_object_or_404(Payment, reservation__pk=reservation_pk)
        if payment.status != Payment.Status.FAILED:
            payment.reservation.status = Reservation.Status.CANCELLED
            payment.reservation.active = False
            payment.reservation.room.available = True
            payment.reservation.room.save()
            payment.reservation.save()

            payment.status = Payment.Status.FAILED
            payment.save()
            logger.info(
                f'payment {payment.pk} for {payment.reservation.pk} successfully canceled'
            )

    except Exception as exc:
        logger.critical(f'unexpected error reverting reservation {reservation_pk}: {str(exc)}')
        messages.error(request, PaymentCancelMessages.UNEXPECTED_ERROR)
        return redirect('rooms')

    return render(request, 'cancel.html')


def stripe_webhook(request: HttpRequest): ...
