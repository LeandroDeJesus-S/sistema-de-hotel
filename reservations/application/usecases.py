"""
Core Concepts Recap
   * Use Case: A single, atomic operation in your application layer that fulfills a business
   goal (e.g., "create a
     reservation").
   * Command/Query DTO: A simple data structure that carries input data into the use case.
   * Result DTO: A simple data structure that carries the output of the use case.
   * Ports: Interfaces that define contracts for external services like databases
   (ReservationRepository), payment systems
     (PaymentGateway), or notifications (NotificationService).

  Here is a proposed structure for your reservations app, mirroring the clients app structure:

    1 reservations/
    2 ├─ domain/
    3 │  ├─ entities.py         # Reservation, Room, etc.
    4 │  ├─ value_objects.py    # DateRange, Money, etc.
    5 │  └─ exceptions.py
    6 ├─ application/
    7 │  ├─ dtos.py             # DTOs for commands and results
    8 │  ├─ ports.py            # ReservationRepository, RoomRepository, etc.
    9 │  └─ usecases/
   10 │     ├─ create_reservation.py
   11 │     ├─ cancel_reservation.py
   12 │     ├─ check_availability.py
   13 │     └─ ...
   14 └─ infra/
   15    ├─ repositories/
   16    │  └─ django_reservation_repository.py
   17    └─ web/
   18       └─ views_adapters.py

  ---

  Client-Facing Use Cases

  These are actions initiated by a hotel guest.

  1. Check Room Availability
   * Responsibility: Determines which rooms (or room types) are available for a given date
   range and number of guests. This
     is a query, not a command, as it doesn't change the system state.
   * Use Case Class: CheckAvailabilityUseCase
   * Input DTO (`AvailabilityQuery`):
       * check_in_date: date
       * check_out_date: date
       * number_of_guests: int
       * room_type_id: Optional[int] (optional, to filter by a specific type)
   * Result DTO (`AvailabilityResult`):
       * available_rooms: List[RoomDTO] (a list of simplified room data)
   * Required Ports:
       * RoomRepository: To find rooms matching the criteria.
       * ReservationRepository: To check for existing, overlapping bookings for those rooms.

  2. Create Reservation
   * Responsibility: The core booking action. It validates availability, business rules
   (e.g., minimum stay), calculates
     the price, and creates the reservation record. It often coordinates with a payment
     process.
   * Use Case Class: CreateReservationUseCase
   * Input DTO (`CreateReservationCommand`):
       * client_id: int
       * room_id: int
       * check_in_date: date
       * check_out_date: date
       * number_of_guests: int
       * payment_token: Optional[str] (if payment is required upfront)
   * Result DTO (`ReservationResult`):
       * success: bool
       * reservation_id: Optional[int]
       * errors: List[str] (e.g., ['room_not_available', 'payment_failed'])
   * Required Ports:
       * ReservationRepository: To check for conflicts and save the new reservation.
       * RoomRepository: To get room details (like price per night).
       * ClientRepository: To verify the client exists.
       * PaymentGateway: (Optional) To process the payment.
       * NotificationService: (Optional) To send a confirmation email.
       * UnitOfWork: To ensure that saving the reservation and processing payment is an atomic
       transaction.

  3. Cancel Reservation
   * Responsibility: Cancels an existing reservation. It must check cancellation policies
   (e.g., "cancellation only allowed
     up to 48 hours before check-in").
   * Use Case Class: CancelReservationUseCase
   * Input DTO (`CancelReservationCommand`):
       * client_id: int (for authorization)
       * reservation_id: int
   * Result DTO (`CancellationResult`):
       * success: bool
       * errors: List[str] (e.g., ['policy_violation_past_deadline'])
   * Required Ports:
       * ReservationRepository: To find and update the reservation's status.
       * PaymentGateway: (Optional) To process a refund if applicable.
       * NotificationService: (Optional) To send a cancellation confirmation.

  4. List My Reservations
   * Responsibility: Fetches a list of all past, present, and future reservations for a
   specific client.
   * Use Case Class: ListUserReservationsUseCase
   * Input DTO (`ListUserReservationsQuery`):
       * client_id: int
   * Result DTO (`UserReservationsResult`):
       * reservations: List[ReservationSummaryDTO]
   * Required Ports:
       * ReservationRepository: To query reservations by client ID.

  ---

  Staff-Facing Use Cases (Admin)

  These are actions performed by hotel employees.

  5. Check-In Guest
   * Responsibility: Marks a reservation as "active" or "checked-in" on the day of arrival.
   * Use Case Class: CheckInUseCase
   * Input DTO (`CheckInCommand`):
       * reservation_id: int
       * staff_id: int (for logging/authorization)
   * Result DTO (`CheckInResult`):
       * success: bool
       * errors: List[str] (e.g., ['reservation_not_found', 'check_in_date_is_in_future'])
   * Required Ports:
       * ReservationRepository: To find the reservation and update its status.

  6. Check-Out Guest
   * Responsibility: Marks a reservation as "completed." May involve calculating final charges
   for services consumed during
     the stay.
   * Use Case Class: CheckOutUseCase
   * Input DTO (`CheckOutCommand`):
       * reservation_id: int
       * staff_id: int
   * Result DTO (`CheckOutResult`):
       * success: bool
       * final_bill: Optional[MoneyDTO]
       * errors: List[str]
   * Required Ports:
       * ReservationRepository: To find and update the reservation.
       * BillingService / ServiceRepository: To fetch and calculate extra charges.
"""

from decimal import Decimal

from clients.domain.ports import AbsClientRepository
from exc import Error, Result

from ..domain.entities import Reservation
from ..domain.repo import AbsReservationRepository, AbsRoomRepository
from .dtos import CreateReservationInput


class InitializeReservationUseCase:
    def __init__(
        self,
        reservation_repo: AbsReservationRepository,
        room_repo: AbsRoomRepository,
        client_repo: AbsClientRepository,
    ):
        self.reservation_repo = reservation_repo
        self.room_repo = room_repo
        self.client_repo = client_repo

    def __call__(self, command: CreateReservationInput) -> Result[Reservation | None]:  # noqa: PLR0911
        """Fetches the room, check if its available then checks for overlapping reservations
        and creates the reservation"""
        try:
            client, err = self.client_repo.get_by_id(command.client_id)
            if err is not None or not client:
                return Result(value=None, error=Error(msg='client not found', src_error=err))

            room_result = self.room_repo.find_by_id(command.room_pk)
            if room_result.error or not room_result.value:
                return Result(
                    value=None, error=Error(msg='room not found', src_error=room_result.error)
                )

            if not room_result.value.available:
                return Result(
                    value=None, error=Error(msg='room not available', src_error=None)
                )

            room = room_result.value
            overlap_result = self.reservation_repo.has_overlapping_reservation(
                room_id=command.room_pk,
                check_in=command.check_in,
                check_out=command.check_out,
            )
            if overlap_result.error or overlap_result.value:
                return Result(
                    value=None,
                    error=Error(msg='The room is not available', src_error=None),
                )

            stayed_days = Decimal(str((command.check_out - command.check_in).days))
            reservation_entity, err = Reservation.safe_create(
                client=client,
                room=room,
                checkin=command.check_in,
                checkout=command.check_out,
                observations=command.observations,
                amount=room.daily_price * stayed_days,
            )

            if err or reservation_entity is None:
                return Result(value=None, error=err)

            saved_reservation_result = self.reservation_repo.save(reservation_entity)
            if saved_reservation_result.error or not saved_reservation_result.value:
                return Result(
                    value=None,
                    error=Error(
                        msg='failed to save reservation',
                        src_error=saved_reservation_result.error,
                    ),
                )

            saved_reservation = saved_reservation_result.value

            room.available = False
            room_save_result = self.room_repo.save(room)
            if room_save_result.error:
                return Result(
                    value=None,
                    error=Error(
                        msg='failed to update room availability',
                        src_error=room_save_result.error,
                    ),
                )

            return Result(value=saved_reservation, error=None)

        except Exception as e:
            return Result(
                value=None,
                error=Error(msg='Unexpected error while creating reservation', src_error=e),
            )


class FetchClientActiveReservations:
    def __init__(self, repository: AbsReservationRepository):
        self._repo = repository

    def __call__(self, client_id: int, include_scheduled: bool) -> Result[list]:
        return self._repo.fetch_active_reservations(client_id, include_scheduled)


class ReleaseRoomUseCase:
    def __init__(self, repo: AbsRoomRepository) -> None:
        self._repo = repo

    def __call__(self) -> None:
        pass


class FetchClientReservationHistoryUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, client_id: int) -> Result[list[Reservation]]:
        return self._repo.fetch_client_history(client_id)


class FetchReservationDetailUseCase:
    def __init__(self, repo: AbsReservationRepository) -> None:
        self._repo = repo

    def __call__(self, reservation_id: int, client_id: int) -> Result[Reservation | None]:
        return self._repo.fetch_for_history_detail(client_id, reservation_id)
