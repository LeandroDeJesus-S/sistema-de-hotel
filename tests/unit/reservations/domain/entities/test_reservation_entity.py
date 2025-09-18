from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from reservations.domain.entities import Reservation
from reservations.feedback_messages import ReserveErrorMessages


@pytest.mark.parametrize(
    'checkin_delta, checkout_delta',
    [
        (1, 2),  # Tomorrow for 1 day
        (10, 20),  # In 10 days for 10 days
    ],
)
def test_reservation_creation_with_valid_data(
    checkin_delta,
    checkout_delta,
    client_fixture,
    room_fixture,
):
    # Given
    checkin = date.today() + timedelta(days=checkin_delta)
    checkout = date.today() + timedelta(days=checkout_delta)

    # When
    reservation = Reservation(
        checkin=checkin,
        checkout=checkout,
        client=client_fixture,
        room=room_fixture,
        observations='No specific observations',
        amount=500.00,
        status='S',
        created_at=date.today(),
    )

    # Then
    assert reservation.checkin == checkin
    assert reservation.checkout == checkout
    assert reservation.client == client_fixture
    assert reservation.room == room_fixture


@pytest.mark.parametrize(
    'checkin_delta, checkout_delta, expected_message',
    [
        (-1, 2, ReserveErrorMessages.INVALID_CHECKIN_DATE),  # Past check-in
        (2, 1, ReserveErrorMessages.INVALID_CHECKIN_DATE),  # Check-out before check-in
        (1, 1, ReserveErrorMessages.INVALID_CHECKIN_DATE),  # Check-out same as check-in
    ],
)
def test_reservation_creation_with_invalid_dates(
    checkin_delta,
    checkout_delta,
    expected_message,
    client_fixture,
    room_fixture,
):
    # Given
    checkin = date.today() + timedelta(days=checkin_delta)
    checkout = date.today() + timedelta(days=checkout_delta)

    # When / Then
    with pytest.raises(ValidationError) as exc_info:
        Reservation(
            checkin=checkin,
            checkout=checkout,
            client=client_fixture,
            room=room_fixture,
            observations='Test',
            amount=100.0,
            status='S',
            created_at=date.today(),
        )

    assert str(expected_message) in str(exc_info.value.errors()[0]['msg'])
