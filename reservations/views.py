import logging
from typing import Any

from dependency_injector.wiring import Provide, inject
from django.contrib import messages
from django.http import Http404, HttpRequest
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from base.dtos import TemplateRenderResultDTO
from reservations.container import ReservationsContainer
from reservations.domain.entities import Reservation
from reservations.domain.repo import AbsReservationRepository
from utils import support

from .application import services
from .infra import presenters
from .mixins import LoginRequired
from .models import Room


@inject
def setup_reservation_context(
    request: HttpRequest,
    context: dict[str, Any],
    svc: services.ReservationService = Provide[ReservationsContainer.reservation_service],
):
    """Adds the reservations to the context.
    Args:
        request (HttpRequest)
        svc (ReservationService)
        context (Any): View context
    """
    if request.user.is_authenticated:
        context['reservations_on'] = svc.fetch_client_active_reservations(
            request.user.pk, include_scheduled=True
        ).unwrap_or([])

    context['benefits'] = svc.room_repo.fetch_all_benefits().unwrap_or([])


class Rooms(ListView):
    """Lists all rooms in the database"""

    model = Room
    template_name = 'rooms.html'
    context_object_name = 'rooms'

    @inject
    def get_queryset(
        self,
        svc: services.ReservationService = Provide[ReservationsContainer.reservation_service],
        logger: logging.Logger = Provide[ReservationsContainer.logger],
    ):
        """Returns all rooms with their benefits"""
        result = svc.room_repo.fetch_all(with_benefits=True, active_only=True)

        def _on_ok(rs):
            logger.debug('successfully loaded rooms')
            return rs

        def _on_err(err):
            logger.error(err.msg, exc_info=err.src_error)
            messages.error(self.request, _('Could not load rooms.'))
            return []

        rooms = result.match(
            on_ok=_on_ok,
            on_err=_on_err,
        )
        return rooms

    def get_context_data(
        self,
        **kwargs,
    ):
        """Returns all rooms, all benefits, and all active or scheduled
        reservations for the client, if any."""
        context = super().get_context_data(**kwargs)
        setup_reservation_context(self.request, context)
        return context


class RoomDetail(DetailView):
    """Shows the details of a specific room"""

    model = Room
    template_name = 'room.html'
    context_object_name = 'room'

    def get_context_data(self, **kwargs):
        """Adds benefits and active or scheduled reservations for the client,
        if any."""
        context = super().get_context_data(**kwargs)
        setup_reservation_context(self.request, context)
        return context


@method_decorator(support.captcha_required('reserve', params=('room_pk',)), 'post')
class Reserve(LoginRequired, View):
    """Manages the creation of new reservations"""

    @inject
    def setup(
        self,
        request: HttpRequest,
        *args: Any,
        svc: services.ReservationService = Provide[ReservationsContainer.reservation_service],
        # room_repo: AbsRoomRepository = Provide[ReservationsContainer.room_repo],
        logger: logging.Logger = Provide[ReservationsContainer.logger],
        **kwargs: Any,
    ) -> None:
        super().setup(request, *args, **kwargs)
        self.logger = logger
        self.svc = svc
        self.template_name = 'reserve.html'

    def get(self, request: HttpRequest, room_pk: int):
        """Renders the form for a new reservation if the user does not
        have an active or scheduled reservation."""
        result = self.svc.render_reserve_form(client_id=request.user.pk, room_id=room_pk)
        return presenters.reserve_get_presenter(request, result, room_pk).unwrap()

    def post(self, request: HttpRequest, room_pk: int):
        self.logger.debug(f'reservation for room {room_pk} started')

        result = self.svc.create_reservation({
            'client_id': request.user.pk,
            'room_pk': room_pk,
            'check_in': request.POST.get('checkin', '0001-01-01'),
            'check_out': request.POST.get('checkout', '0001-01-01'),
            'observations': request.POST.get('obs', ''),
            'currency': request.POST.get('currency'),
        })

        return presenters.reserve_post_presenter(request, result).unwrap()


class ReservationsHistory(LoginRequired, ListView):
    """Displays the user's reservation history"""

    template_name = 'reservations_history.html'
    context_object_name = 'reservations'

    def setup(
        self,
        request,
        *args,
        svc: services.ReservationService = Provide[ReservationsContainer.reservation_service],
        logger: logging.Logger = Provide[ReservationsContainer.logger],
        **kwargs,
    ):
        super().setup(request, *args, **kwargs)
        self.svc = svc
        self.logger = logger

    def get_queryset(self) -> list[Reservation]:
        result = self.svc.fetch_client_reservation_history(client_id=self.request.user.pk)

        def _on_err(err) -> list[Reservation]:
            self.logger.error(err.msg, exc_info=err.src_error)
            messages.error(self.request, err.msg)
            return []

        reservations: list[Reservation] = result.match(
            on_ok=lambda rs: rs,
            on_err=_on_err,
        )
        return reservations

    def get_context_data(
        self,
        reservation_repo: AbsReservationRepository = Provide[
            ReservationsContainer.reservation_repo
        ],
        **kwargs,
    ):
        """Add cancellation eligibility information."""
        context = super().get_context_data(**kwargs)
        context['reservation_items'] = self.svc.get_reservations_with_cancellation_info(
            context['reservations']
        )
        user_id: int = self.request.user.pk
        context['can_create_reservation'] = not reservation_repo.has_active_reservation(
            user_id, include_scheduled=True
        ).unwrap_or(False)
        return context


class ReservationHistory(LoginRequired, DetailView):
    """Displays the data of a specific reservation from the reservation history"""

    template_name = 'reservation_history.html'

    @inject
    def get_context_data(
        self,
        svc: services.ReservationService = Provide[ReservationsContainer.reservation_service],
        reservation_repo: AbsReservationRepository = Provide[
            ReservationsContainer.reservation_repo
        ],
        **kwargs,
    ):
        """Add cancellation eligibility information."""
        context = super().get_context_data(**kwargs)

        user_id: int = self.request.user.pk
        context['can_create_reservation'] = not reservation_repo.has_active_reservation(
            user_id, include_scheduled=True
        ).unwrap_or(False)

        result_dto = svc.fetch_reservation_detail(
            reservation_id=self.kwargs.get('pk'), client_id=self.request.user.pk
        )
        res = result_dto.unwrap_or(None)
        if not isinstance(res, TemplateRenderResultDTO):
            raise Http404(_('Reservation not found'))

        context.update(res.context)
        return context

    def get_object(self, _=None):
        return None  # just ensures that the reseration is returned by `get_context_data`


@method_decorator(support.captcha_required('cancel_reservation', params=('pk',)), 'post')
class CancelReservationView(LoginRequired, View):
    """Handle reservation cancellation requests."""

    @inject
    def get(
        self,
        request,
        pk,
        svc: services.ReservationService = Provide[ReservationsContainer.reservation_service],
    ):
        """Show cancellation confirmation page."""
        result = svc.fetch_reservation_detail(reservation_id=pk, client_id=request.user.pk)
        return presenters.cancel_reservation_get_presenter(request, result).unwrap()

    @inject
    def post(
        self,
        request,
        pk,
        svc: services.ReservationService = Provide[ReservationsContainer.reservation_service],
    ):
        """Process reservation cancellation."""
        reason = request.POST.get('reason', '').strip()
        result = svc.cancel_reservation(pk, request.user.pk, reason)

        return presenters.cancel_reservation_post_presenter(request, result).unwrap()
