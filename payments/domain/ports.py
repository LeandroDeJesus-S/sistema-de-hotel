from typing import Protocol

from exc import Result


class AbsPaymentsRepository(Protocol):
    def confirm_reservation_payment(self, reservation_id: int) -> Result[bool]: ...
