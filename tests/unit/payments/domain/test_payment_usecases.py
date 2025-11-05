import logging
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.entities import Client
from exc import Result
from payments.application.dtos import CheckoutUseCaseInputDTO
from payments.application.usecases import CheckoutUseCase
from payments.domain.dtos import (
    CheckoutItemDTO,
    CheckoutResultDTO as DomainCheckoutResultDTO,
    CheckoutSessionInputDTO,
)
from payments.domain.entities import Payment
from payments.domain.ports import AbsPaymentsRepository, AbsSessionBasedPayment
from reservations.domain.entities import Reservation
from utils.support import model_to_entity


@pytest.fixture
def mock_payment_repo():
    return MagicMock(spec=AbsPaymentsRepository)


@pytest.fixture
def mock_payment_gateway():
    return MagicMock(spec=AbsSessionBasedPayment)


@pytest.fixture
def mock_uow():
    return MagicMock(spec=AbsUnitOfWork)


@pytest.fixture
def mock_logger():
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def checkout_use_case(
    mock_payment_repo, mock_payment_gateway, mock_uow, mock_logger
):
    return CheckoutUseCase(
        payment_repo=mock_payment_repo,
        payment_gateway=mock_payment_gateway,
        uow=mock_uow,
        logger=mock_logger,
    )


@pytest.fixture
def checkout_use_case_input_dto(reservation_model, client_model) -> CheckoutUseCaseInputDTO:
    reservation = model_to_entity(reservation_model, Reservation).unwrap()
    return CheckoutUseCaseInputDTO(
        client=model_to_entity(client_model, Client).unwrap(),
        reservation=reservation,
        checkout_session_input=CheckoutSessionInputDTO(
            currency='brl',
            expires_at=timezone.now() + timedelta(minutes=30),
            success_url='http://test.com/success',
            return_url='http://test.com/cancel',
            items=[
                CheckoutItemDTO(
                    name=f'Reserva para {reservation.room.room_class}',
                    unit_price_cents=int(reservation.room.daily_price * 100),
                    quantity=reservation.reservation_days().unwrap(),
                )
            ],
        ),
    )


def test_checkout_use_case_success(
    checkout_use_case: CheckoutUseCase,
    checkout_use_case_input_dto: CheckoutUseCaseInputDTO,
    mock_payment_repo: MagicMock,
    mock_payment_gateway: MagicMock,
    mock_uow: MagicMock,
):
    # Arrange
    domain_result = DomainCheckoutResultDTO(
        session_id='12345', client_id='123', session_url='http://stripe.com/session'
    )
    mock_payment_gateway.create_checkout_session.return_value = Result.Ok(domain_result)
    mock_payment_repo.create.return_value = Result.Ok(MagicMock(spec=Payment))

    # Act
    result = checkout_use_case(checkout_use_case_input_dto)

    # Assert
    assert result.is_ok()
    assert isinstance(result.unwrap(), DomainCheckoutResultDTO)
    assert result.unwrap().session_url == domain_result.session_url

    mock_payment_gateway.create_checkout_session.assert_called_once_with(
        checkout_use_case_input_dto.checkout_session_input
    )
    mock_payment_repo.create.assert_called_once()
    mock_uow.__enter__.assert_called_once()


def test_checkout_use_case_repo_failure(
    checkout_use_case: CheckoutUseCase,
    checkout_use_case_input_dto: CheckoutUseCaseInputDTO,
    mock_payment_repo: MagicMock,
    mock_payment_gateway: MagicMock,
    mock_uow: MagicMock,
):
    # Arrange
    domain_result = DomainCheckoutResultDTO(
        session_id='12345', client_id='123', session_url='http://stripe.com/session'
    )
    mock_payment_gateway.create_checkout_session.return_value = Result.Ok(domain_result)
    mock_payment_repo.create.return_value = Result.Err('DB error')

    # Act
    result = checkout_use_case(checkout_use_case_input_dto)

    # Assert
    assert result.is_err()
    assert 'Failed to create payment' in result.unwrap_err().msg
    mock_uow.__enter__.assert_called_once()
    mock_uow.__enter__().rollback.assert_called_once()
