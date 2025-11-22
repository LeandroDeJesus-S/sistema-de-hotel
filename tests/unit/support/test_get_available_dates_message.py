from datetime import date

import pytest

from utils.support import get_available_dates_message


class MockReservationEntity:
    """A mock class to simulate the ReservationEntity."""

    def __init__(self, checkin, checkout):
        self.checkin = checkin
        self.checkout = checkout


def test_with_no_reservations():
    """Should raise UnboundLocalError when no reservations are provided."""
    with pytest.raises(UnboundLocalError):
        get_available_dates_message([])


def test_with_one_reservation(mocker):
    """Should show availability from the checkout date onwards for a single reservation."""
    mocker.patch('utils.support.gt', side_effect=lambda s: s)
    mocker.patch('utils.support.gtl', side_effect=lambda s: s)
    reservations = [
        MockReservationEntity(checkin=date(2023, 1, 10), checkout=date(2023, 1, 15))
    ]
    message = get_available_dates_message(reservations).unwrap()
    assert message == 'Este quarto só está disponível para reserva apartir de 15/01/2023.'


def test_with_contiguous_reservations(mocker):
    """Should show availability from the last checkout date for contiguous reservations."""
    mocker.patch('utils.support.gt', side_effect=lambda s: s)
    mocker.patch('utils.support.gtl', side_effect=lambda s: s)
    reservations = [
        MockReservationEntity(checkin=date(2023, 1, 10), checkout=date(2023, 1, 15)),
        MockReservationEntity(checkin=date(2023, 1, 15), checkout=date(2023, 1, 20)),
    ]
    message = get_available_dates_message(reservations).unwrap()
    assert message == 'Este quarto só está disponível para reserva apartir de 20/01/2023.'


def test_with_one_gap(mocker):
    """Should show the available date range between two reservations."""
    mocker.patch('utils.support.gt', side_effect=lambda s: s)
    mocker.patch('utils.support.gtl', side_effect=lambda s: s)
    reservations = [
        MockReservationEntity(checkin=date(2023, 1, 10), checkout=date(2023, 1, 15)),
        MockReservationEntity(checkin=date(2023, 1, 20), checkout=date(2023, 1, 25)),
    ]
    message = get_available_dates_message(reservations).unwrap()
    assert (
        message
        == '15/01/2023 a 19/01/2023, Este quarto só está disponível para reserva apartir de, e 25/01/2023 para frente.'
    )


def test_with_multiple_gaps(mocker):
    """Should show all available date ranges for multiple reservations with gaps."""
    mocker.patch('utils.support.gt', side_effect=lambda s: s)
    mocker.patch('utils.support.gtl', side_effect=lambda s: s)
    reservations = [
        MockReservationEntity(checkin=date(2023, 1, 10), checkout=date(2023, 1, 12)),
        MockReservationEntity(checkin=date(2023, 1, 15), checkout=date(2023, 1, 17)),
        MockReservationEntity(checkin=date(2023, 1, 20), checkout=date(2023, 1, 22)),
    ]
    message = get_available_dates_message(reservations).unwrap()
    assert (
        message
        == '12/01/2023 a 14/01/2023, 17/01/2023 a 19/01/2023, Este quarto só está disponível para reserva apartir de, e 22/01/2023 para frente.'
    )


def test_with_one_day_gap(mocker):
    """Should correctly handle a single day gap."""
    mocker.patch('utils.support.gt', side_effect=lambda s: s)
    mocker.patch('utils.support.gtl', side_effect=lambda s: s)
    reservations = [
        MockReservationEntity(checkin=date(2023, 1, 10), checkout=date(2023, 1, 12)),
        MockReservationEntity(checkin=date(2023, 1, 13), checkout=date(2023, 1, 15)),
    ]
    message = get_available_dates_message(reservations).unwrap()
    assert (
        message
        == '12/01/2023 a 12/01/2023, Este quarto só está disponível para reserva apartir de, e 15/01/2023 para frente.'
    )
