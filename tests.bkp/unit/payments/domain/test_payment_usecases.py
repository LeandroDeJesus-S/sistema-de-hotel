import logging
from unittest.mock import MagicMock, create_autospec

import pytest

from base.ports.email import AbsEmailSender
from base.ports.pdf import AbsPDFGenerator
from base.ports.queue import TaskQueuer
from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.entities import Client
from clients.domain.ports import AbsClientRepository
from exc import Result
from payments.application.dtos import CheckoutUseCaseInputDTO
from payments.application.usecases import CheckoutUseCase, SendPaymentConfirmationUseCase
from payments.domain.dtos import (
    CheckoutResultDTO as DomainCheckoutResultDTO,
)
from payments.domain.entities import Payment
from payments.domain.ports import AbsPaymentsRepository, AbsSessionBasedPayment
from reservations.domain.entities import Reservation, RoomClass
from reservations.domain.repo import AbsReservationRepository
from utils.support import model_to_entity


@pytest.fixture
def mock_payment_repo():
    return MagicMock(spec=AbsPaymentsRepository)


@pytest.fixture
def mock_client_repo():
    return MagicMock(spec=AbsClientRepository)


@pytest.fixture
def mock_reservation_repo():
    return create_autospec(AbsReservationRepository)


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
def mock_pdf_generator():
    return MagicMock(spec=AbsPDFGenerator)


@pytest.fixture
def mock_email_sender():
    return MagicMock(spec=AbsEmailSender)


@pytest.fixture
def mock_task_queue():
    return MagicMock(spec=TaskQueuer)


@pytest.fixture
def checkout_use_case(
    mock_payment_repo,
    mock_payment_gateway,
    mock_uow,
    mock_logger,
    mock_client_repo,
    mock_reservation_repo,
):
    return CheckoutUseCase(
        payment_repo=mock_payment_repo,
        payment_gateway=mock_payment_gateway,
        uow=mock_uow,
        logger=mock_logger,
        client_repo=mock_client_repo,
        reservation_repo=mock_reservation_repo,
    )


@pytest.fixture
def send_confirmation_use_case(
    mock_email_sender: AbsEmailSender,
    mock_pdf_generator: AbsPDFGenerator,
):
    return SendPaymentConfirmationUseCase(
        mailer=mock_email_sender,
        pdf_generator=mock_pdf_generator,
    )


@pytest.fixture
def checkout_use_case_input_dto(reservation_model, client_model) -> CheckoutUseCaseInputDTO:
    reservation = model_to_entity(reservation_model, Reservation).unwrap()
    client = model_to_entity(client_model, Client).unwrap()
    return CheckoutUseCaseInputDTO(
        client_id=client.id,
        reservation_id=reservation.id,
        success_url='http://test.com/success',
        cancel_url='http://test.com/cancel',
    )


def test_checkout_use_case_success(
    checkout_use_case: CheckoutUseCase,
    checkout_use_case_input_dto: CheckoutUseCaseInputDTO,
    mock_payment_repo: MagicMock,
    mock_payment_gateway: MagicMock,
    mock_uow: MagicMock,
    mock_client_repo: MagicMock,
    mock_reservation_repo: MagicMock,
    reservation_model,
    client_model,
):
    # Arrange
    mock_client = model_to_entity(client_model, Client).unwrap()
    mock_client_repo.get_by_id.return_value = Result.Ok(mock_client)

    room_class_mock = MagicMock(spec=RoomClass)
    room_class_mock.name = "test"

    mock_reservation = model_to_entity(reservation_model, Reservation).unwrap()
    mock_reservation_repo.find_by_id.return_value = Result.Ok(mock_reservation)

    mock_payment = MagicMock(spec=Payment, id=1, client=mock_client, reservation=mock_reservation)
    mock_payment_repo.get_pending_from.return_value = Result.Ok(None)
    mock_payment_repo.create.return_value = Result.Ok(mock_payment)
    mock_payment_repo.update.return_value = Result.Ok(mock_payment)

    domain_result = DomainCheckoutResultDTO(
        session_id='12345', client_id='123', session_url='http://stripe.com/session'
    )
    mock_payment_gateway.create_checkout_session.return_value = Result.Ok(domain_result)

    # Act
    result = checkout_use_case(checkout_use_case_input_dto)

    # Assert
    assert result.is_ok(), result.unwrap_err()
    assert isinstance(result.unwrap(), DomainCheckoutResultDTO)
    assert result.unwrap().session_url == domain_result.session_url

    mock_payment_gateway.create_checkout_session.assert_called_once()
    mock_payment_repo.create.assert_called_once()
    mock_uow.__enter__.assert_called_once()


def test_checkout_use_case_repo_failure(
    checkout_use_case: CheckoutUseCase,
    checkout_use_case_input_dto: CheckoutUseCaseInputDTO,
    mock_payment_repo: MagicMock,
    mock_payment_gateway: MagicMock,
    mock_uow: MagicMock,
    mock_client_repo: MagicMock,
    mock_reservation_repo: MagicMock,
    reservation_model,
):
    # Arrange
    domain_result = DomainCheckoutResultDTO(
        session_id='12345', client_id='123', session_url='http://stripe.com/session'
    )
    mock_payment_gateway.create_checkout_session.return_value = Result.Ok(domain_result)
    mock_payment_repo.get_pending_from.return_value = Result.Ok(None)
    mock_payment_repo.create.return_value = Result.Err('DB error')
    mock_client_repo.get_by_id.return_value = Result.Ok(MagicMock(spec=Client))
    mock_reservation_repo.find_by_id.return_value = model_to_entity(reservation_model, Reservation)

    # Act
    result = checkout_use_case(checkout_use_case_input_dto)

    # Assert
    assert result.is_err()
    assert 'Failed to create payment' == result.unwrap_err().msg, str(result.unwrap_err())
    mock_uow.__enter__.assert_called_once()
    mock_uow.__enter__().rollback.assert_called_once()


def test_send_payment_confirmation_success(
    send_confirmation_use_case: SendPaymentConfirmationUseCase,
    mock_email_sender: MagicMock,
    mock_pdf_generator: MagicMock,
):
    # given
    mock_payment = MagicMock(spec=Payment)
    mock_payment.id = 1
    mock_payment.reservation = MagicMock(spec=Reservation)
    mock_payment.reservation.room = MagicMock()
    mock_payment.reservation.room.number = "101"
    mock_payment.reservation.client = MagicMock(spec=Client)
    mock_payment.reservation.client.email = "test@example.com"
    mock_pdf_generator.generate.return_value = Result.Ok(b"some pdf bytes")
    mock_email_sender.send_single_mail.return_value = Result.Ok(None)

    # when
    result = send_confirmation_use_case(payment=mock_payment)

    # then
    assert result.is_ok()
    mock_pdf_generator.generate.assert_called_once_with(mock_payment)
    mock_email_sender.send_single_mail.assert_called_once()
