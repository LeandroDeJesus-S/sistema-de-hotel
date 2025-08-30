from datetime import date, timedelta

import pytest
from ddf import G
from django.core.exceptions import ValidationError

from reservations.models import Reservation
from schedules.models import Scheduling
from utils.supportmodels import ReserveErrorMessages


@pytest.mark.django_db
def test_scheduling_model_with_valid_data(client_fixture, room_fixture):
    """
    Should create a Scheduling instance successfully when valid data is provided.
    This includes a room that is already occupied by an active reservation,
    and the new reservation dates do not overlap with any existing active/scheduled reservations.
    """
    # Arrange
    # Create an active reservation to simulate an occupied room
    occupied_checkin = date.today() + timedelta(days=1)
    occupied_checkout = occupied_checkin + timedelta(days=5)
    occupied_reservation = G(
        Reservation,
        client=client_fixture,
        room=room_fixture,
        checkin=occupied_checkin,
        checkout=occupied_checkout,
        status='A',
        active=True,
    )

    # Create a new reservation that does not overlap with the occupied reservation
    new_checkin = occupied_checkout + timedelta(days=1)
    new_checkout = new_checkin + timedelta(days=3)
    new_reservation = G(
        Reservation,
        client=client_fixture,
        room=room_fixture,
        checkin=new_checkin,
        checkout=new_checkout,
        status='I',
    )

    scheduling = Scheduling(client=client_fixture, reservation=new_reservation)

    # Act & Assert
    try:
        scheduling.full_clean()
    except ValidationError as e:
        pytest.fail(f'ValidationError raised with valid data: {e.message_dict}')


@pytest.mark.django_db
@pytest.mark.parametrize(
    'scenario, expected_error_message_key, setup_reservations_func',
    [
        (
            'room_not_occupied',
            'reservation',
            lambda client, room: G(
                Reservation,
                client=client,
                room=room,
                checkin=date.today() + timedelta(days=1),
                checkout=date.today() + timedelta(days=3),
                status='I',
            ),
        ),
        (
            'date_overlap',
            'reservation',
            lambda client, room: [
                G(
                    Reservation,
                    client=client,
                    room=room,
                    checkin=date.today() + timedelta(days=5),
                    checkout=date.today() + timedelta(days=10),
                    status='A',
                    active=True,
                ),
                G(
                    Reservation,
                    client=client,
                    room=room,
                    checkin=date.today() + timedelta(days=7),
                    checkout=date.today() + timedelta(days=12),
                    status='I',
                ),
            ],
        ),
    ],
    ids=['room_not_occupied', 'date_overlap'],
)
def test_scheduling_model_with_invalid_data(
    client_fixture, room_fixture, scenario, expected_error_message_key, setup_reservations_func
):
    """
    Should raise ValidationError for invalid Scheduling scenarios.
    """
    # Arrange
    if scenario == 'room_not_occupied':
        new_reservation = setup_reservations_func(client_fixture, room_fixture)
        scheduling = Scheduling(client=client_fixture, reservation=new_reservation)
        expected_message = 'Não é possível agendar um quarto que não esta ocupado.'
    elif scenario == 'date_overlap':
        existing_reservation, new_reservation = setup_reservations_func(
            client_fixture, room_fixture
        )
        scheduling = Scheduling(client=client_fixture, reservation=new_reservation)
        # The exact message depends on the dates, so we'll check for the key and part of the message
        expected_message = ReserveErrorMessages.UNAVAILABLE_DATE.split('{dates}')[
            0
        ]  # Get the part before {dates}

    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        scheduling.full_clean()

    assert expected_error_message_key in excinfo.value.message_dict
    if scenario == 'room_not_occupied':
        assert excinfo.value.message_dict[expected_error_message_key][0] == expected_message
    elif scenario == 'date_overlap':
        assert expected_message in excinfo.value.message_dict[expected_error_message_key][0]
