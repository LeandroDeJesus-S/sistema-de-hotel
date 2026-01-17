from abc import abstractmethod
from datetime import datetime
from typing import Protocol

from exc import Result

from . import entities


class AbsReservationRepository(Protocol):
    @abstractmethod
    def fetch_active_reservations(
        self, client_id: int, include_scheduled: bool = False
    ) -> Result[list[entities.Reservation]]:
        """Returns a list of active reservations for a given client."""
        ...

    @abstractmethod
    def has_active_reservation(self, client_id: int, include_scheduled: bool) -> Result[bool]:
        """Returns True if the client has an active reservation."""
        ...

    @abstractmethod
    def has_overlapping_reservation(
        self,
        room_id: int,
        check_in: datetime,
        check_out: datetime,
    ) -> Result[bool]:
        """Checks if there are any active or scheduled reservations for a given room and
        datetime range."""
        ...

    @abstractmethod
    def save(self, reservation: entities.Reservation) -> Result[entities.Reservation]:
        """Saves a reservation to the repository."""
        ...

    @abstractmethod
    def fetch_client_history(self, client_id: int) -> Result[list[entities.Reservation]]:
        """Fetches the reservation history for a given client."""
        ...

    @abstractmethod
    def fetch_for_history_detail(
        self, client_id: int, reservation_id: int
    ) -> Result[entities.Reservation]:
        """Fetches a specific reservation detail for the history view."""
        ...

    @abstractmethod
    def find_by_id(self, id: int) -> Result[entities.Reservation]:
        """Finds a reservation by its ID."""
        ...

    @abstractmethod
    def from_room(
        self, room_id: int, occuped_only: bool = False
    ) -> Result[list[entities.Reservation]]:
        """Fetches all reservations for a given room."""
        ...

    @abstractmethod
    def fetch_pending(
        self, client_id: int, room_id: int, check_in: datetime, check_out: datetime
    ) -> Result[entities.Reservation]:
        """Fetches a pending reservation for a client, room and datetime range."""
        ...

    @abstractmethod
    def fetch_all_active(self) -> Result[list[entities.Reservation]]:
        """Fetches all active reservations."""
        ...


class AbsBenefitRepository(Protocol):
    @abstractmethod
    def fetch_all(self) -> Result[list[entities.Benefit]]:
        """Fetches all benefits from the repository."""
        ...

    @abstractmethod
    def save(self, benefit: entities.Benefit) -> Result[entities.Benefit]:
        """Saves a benefit to the repository."""
        ...


class AbsRoomRepository(Protocol):
    @abstractmethod
    def find_by_id(self, id: int) -> Result[entities.Room]:
        """Finds a room by its ID."""
        ...

    @abstractmethod
    def fetch_all(self, with_benefits: bool = False) -> Result[list[entities.Room]]:
        """Fetches all rooms from the repository."""
        ...

    @abstractmethod
    def fetch_all_benefits(self) -> Result[list[entities.Benefit]]:
        """Fetches all room benefits."""
        ...

    @abstractmethod
    def fetch_all_classes(self) -> Result[list[entities.RoomClass]]:
        """Fetches all room classes."""
        ...

    @abstractmethod
    def save(self, room: entities.Room) -> Result[entities.Room]:
        """Saves a room to the repository."""
        ...
