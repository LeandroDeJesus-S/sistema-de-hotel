"""
This module provides concrete implementations of the reservation-related ports.
"""

import logging
from datetime import date

from django.core.exceptions import ValidationError

from exc import Error, Result
from reservations.domain import entities
from reservations.domain.repo import (
    AbsReservationRepository,
    AbsRoomRepository,
)
from reservations.models import (
    Benefit as BenefitModel,
)
from reservations.models import (
    Class as ClassModel,
)
from reservations.models import (
    Reservation as ReservationModel,
)
from reservations.models import (
    Room as RoomModel,
)
from utils.support import (
    entity_to_model,
    model_to_entity,
    models_to_entities,
)

from ..domain.value_objects import ReservationStatusEnum

logger = logging.getLogger('djangoLogger')


class RoomRepository(AbsRoomRepository):
    """
    A concrete repository for Room entities that uses Django's ORM.
    """

    def __init__(self):
        self._modelclass = RoomModel
        self._room_entity_class = entities.Room
        self._benefit_entity_class = entities.Benefit
        self._room_class_entity_class = entities.RoomClass

    def find_by_id(self, id: int) -> Result[entities.Room | None]:
        room = (
            self._modelclass.objects.select_related('room_class', 'hotel')
            .filter(id=id)
            .first()
        )
        if room is None:
            return Result(value=None, error=Error(msg='Room not found', src_error=None))

        r, err = model_to_entity(room, self._room_entity_class)
        return Result(value=r, error=err)

    def fetch_all(self, with_benefits: bool = False) -> Result[list[entities.Room]]:
        try:
            rooms_qs = self._modelclass.objects.select_related('room_class', 'hotel').all()
            if with_benefits:
                rooms_qs = rooms_qs.prefetch_related('benefits')

            logger.debug(f'rooms_qs: {rooms_qs}')
            rooms = rooms_qs.order_by('-daily_price')
            room_entities = []
            for r in rooms:
                e, err = model_to_entity(r, self._room_entity_class)
                if err or not e:
                    return Result(
                        value=[], error=Error(msg='Could not fetch rooms', src_error=err)
                    )

                if with_benefits:
                    e.benefits, err2 = models_to_entities(
                        r.benefits.all(), self._benefit_entity_class
                    )
                    if err2:
                        return Result(
                            value=[],
                            error=Error(msg='Could not fetch benefits', src_error=err2),
                        )

                room_entities.append(e)

            return Result(value=room_entities, error=None)
        except Exception as e:
            return Result(value=[], error=Error(msg='Could not fetch rooms', src_error=e))

    def fetch_all_benefits(self) -> Result[list[entities.Benefit]]:
        try:
            benefits = BenefitModel.objects.all()
            benefit_entities, err = models_to_entities(benefits, self._benefit_entity_class)
            if err:
                return Result(
                    value=[], error=Error(msg='Could not fetch benefits', src_error=err)
                )
            return Result(value=benefit_entities, error=None)
        except Exception as e:
            return Result(value=[], error=Error(msg='Could not fetch benefits', src_error=e))

    def fetch_all_classes(self) -> Result[list[entities.RoomClass]]:
        try:
            classes = ClassModel.objects.all()
            return models_to_entities(classes, self._room_class_entity_class)
        except Exception as e:
            return Result(
                value=[], error=Error(msg='Could not fetch room classes', src_error=e)
            )

    def save(self, room: entities.Room) -> Result[entities.Room | None]:
        # HACK: should I keep m2m logic here? I don't think so

        # Extract M2M data before converting
        benefits_data = room.benefits.copy()

        model_instance_result = entity_to_model(room, self._modelclass)
        if model_instance_result.error:
            return Result(value=None, error=model_instance_result.error)

        model_instance = model_instance_result.value
        if not model_instance:
            return Result(
                value=None, error=Error(msg='Failed to convert room entity to model')
            )

        try:
            model_instance.full_clean()
            model_instance.save()

            # Handle M2M relationship
            if benefits_data:
                benefit_ids = [b.id for b in benefits_data if b.id is not None]
                model_instance.benefits.set(benefit_ids)

        except ValidationError as e:
            return Result(value=None, error=Error(msg='Invalid room', src_error=e))
        except Exception as e:
            logger.error(f'DB error on room save: {e}', exc_info=True)
            return Result(value=None, error=Error(msg='Could not save room', src_error=e))

        return model_to_entity(model_instance, self._room_entity_class)


class ReservationRepository(AbsReservationRepository):
    """
    A concrete repository for Reservation entities that uses Django's ORM.
    """

    def __init__(self):
        self._modelclass = ReservationModel
        self._entityclass = entities.Reservation

    def save(self, reservation: entities.Reservation) -> Result[entities.Reservation | None]:
        model_instance_result = entity_to_model(reservation, self._modelclass)
        if model_instance_result.error:
            return Result(value=None, error=model_instance_result.error)

        model_instance = model_instance_result.value
        if not model_instance:
            return Result(
                value=None, error=Error(msg='Failed to convert reservation entity to model')
            )

        try:
            model_instance.full_clean()
            model_instance.save()
        except ValidationError as e:
            return Result(value=None, error=Error(msg='Invalid reservation', src_error=e))
        except Exception as e:
            logger.error(f'DB error on reservation save: {e}', exc_info=True)
            return Result(
                value=None, error=Error(msg='Could not save reservation', src_error=e)
            )

        return model_to_entity(model_instance, self._entityclass)

    def has_overlapping_reservation(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
    ) -> Result[bool]:
        try:
            exists = self._modelclass.objects.filter(
                room_id=room_id,
                checkout__gte=check_in,
                checkin__lt=check_out,
                status__in=[
                    ReservationStatusEnum.ACTIVE.value,
                    ReservationStatusEnum.SCHEDULED.value,
                ],
            ).exists()
            return Result(value=exists, error=None)
        except Exception as e:
            return Result(
                value=False,
                error=Error(msg='Could not check for overlapping reservations', src_error=e),
            )

    def fetch_active_reservations(
        self, client_id: int, include_scheduled: bool = False
    ) -> Result[list[entities.Reservation]]:
        statuses = [ReservationStatusEnum.ACTIVE.value]  # Ativa
        if include_scheduled:
            statuses.append(ReservationStatusEnum.SCHEDULED.value)  # Agendada

        try:
            reservations = self._modelclass.objects.filter(
                client_id=client_id, status__in=statuses
            ).order_by('-id')

            reservation_entities, err = models_to_entities(reservations, self._entityclass)
            if err is not None:
                return Result(
                    value=[], error=Error(msg='Could not fetch reservation', src_error=err)
                )

            return Result(value=reservation_entities, error=None)
        except Exception as e:
            return Result(
                value=[], error=Error(msg='Could not fetch active reservations', src_error=e)
            )

    def has_active_reservation(self, client_id: int, include_scheduled: bool) -> Result[bool]:
        statuses = [ReservationStatusEnum.ACTIVE.value]
        if include_scheduled:
            statuses.append(ReservationStatusEnum.SCHEDULED.value)
        try:
            exists = self._modelclass.objects.filter(
                client_id=client_id, status__in=statuses
            ).exists()
            return Result(value=exists, error=None)
        except Exception as e:
            return Result(
                value=False,
                error=Error(msg='Could not check for active reservation', src_error=e),
            )

    def fetch_client_history(self, client_id: int) -> Result[list[entities.Reservation]]:
        try:
            reservations = self._modelclass.objects.filter(
                client_id=client_id,
                status__in=[
                    ReservationStatusEnum.ACTIVE.value,
                    ReservationStatusEnum.SCHEDULED.value,
                    ReservationStatusEnum.CANCELLED.value,
                    ReservationStatusEnum.FINISHED.value,
                ],
            ).order_by('-id')

            reservation_entities, err = models_to_entities(reservations, self._entityclass)
            if err is not None:
                return Result(
                    value=[],
                    error=Error(msg='Could not parse reservation to entity', src_error=err),
                )

            return Result(value=reservation_entities, error=None)
        except Exception as e:
            return Result(
                value=[], error=Error(msg='Could not fetch client history', src_error=e)
            )

    def fetch_for_history_detail(
        self, client_id: int, reservation_id: int
    ) -> Result[entities.Reservation | None]:
        reservation = self._modelclass.objects.filter(
            pk=reservation_id,
            client__id=client_id,
            status__in=[
                ReservationStatusEnum.ACTIVE.value,
                ReservationStatusEnum.SCHEDULED.value,
                ReservationStatusEnum.CANCELLED.value,
                ReservationStatusEnum.FINISHED.value,
            ],
        ).first()
        if reservation is None:
            return Result(value=None, error=Error(msg='Reservation not found'))

        entity, err = model_to_entity(reservation, self._entityclass)
        if entity:
            return Result(value=entity, error=None)

        return Result(value=None, error=Error(msg='Reservation not found', src_error=err))
