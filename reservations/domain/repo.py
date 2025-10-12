from datetime import date
from typing import Protocol

from exc import Result

from . import entities


class AbsReservationRepository(Protocol):
    def fetch_active_reservations(
        self, client_id: int, include_scheduled: bool = False
    ) -> Result[list[entities.Reservation]]:
        """Returns a list of active reservations for a given client."""

    def has_active_reservation(self, client_id: int, include_scheduled: bool) -> Result[bool]:
        """Returns True if the client has an active reservation."""

    def has_overlapping_reservation(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
    ) -> Result[bool]:
        """Checks if there are any active or scheduled reservations for a given room and date
        range."""

    def save(
        self, reservation: entities.Reservation
    ) -> Result[entities.Reservation | None]: ...
    def fetch_client_history(self, client_id: int) -> Result[list[entities.Reservation]]: ...
    def fetch_for_history_detail(
        self, client_id: int, reservation_id: int
    ) -> Result[entities.Reservation | None]: ...
    def find_by_id(self, id: int) -> Result[entities.Reservation | None]: ...


class AbsBenefitRepository(Protocol):
    def fetch_all(self) -> Result[list[entities.Benefit]]: ...
    def save(self, benefit: entities.Benefit) -> Result[entities.Benefit | None]: ...


class AbsRoomRepository(Protocol):
    def find_by_id(self, id: int) -> Result[entities.Room | None]: ...
    def fetch_all(self, with_benefits: bool = False) -> Result[list[entities.Room]]: ...
    def fetch_all_benefits(self) -> Result[list[entities.Benefit]]: ...
    def fetch_all_classes(self) -> Result[list[entities.RoomClass]]: ...
    def save(self, room: entities.Room) -> Result[entities.Room | None]: ...
