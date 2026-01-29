import pytest
from datetime import datetime, timezone
from exc import Result, Error

from payments.application.dtos import CheckoutUseCaseInputDTO
from payments.application.usecases import CheckoutUseCase
from payments.domain.dtos import CheckoutResultDTO, CheckoutSessionInputDTO
from payments.domain.entities import PaymentGateway, PaymentStatus
from reservations.domain.value_objects import Currency

class TestCheckoutUseCase:
    @pytest.fixture
    def mock_reservation(self, mocker):
        res = mocker.Mock()
        res.reservation_days.return_value = Result.Ok(5)
        res.room.number = '101'
        res.room.room_class.name = 'Standard'
        res.currency = Currency.USD
        res.price = 100000
        res.id = 1
        return res

    @pytest.fixture
    def mock_payment(self, mocker, mock_reservation):
        pay = mocker.Mock()
        pay.id = 1
        pay.gateway_payment_session_id = None
        pay.reservation = mock_reservation
        return pay

    def test_successful_checkout_creates_new_payment_and_session(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        mock_reservation,
        mock_payment,
    ):
        """Should create a new payment and checkout session when no pending payment exists."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(mocker.Mock())
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

        session_result = CheckoutResultDTO.safe_create(
            client_id='client_123', session_id='session_123', session_url='http://checkout.com'
        ).unwrap()
        mock_session_based_payment.create_checkout_session.return_value = Result.Ok(
            session_result
        )

        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Ok(mock_payment)
        mock_payments_repository.update.return_value = Result.Ok(mock_payment)

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_ok()
        assert result.unwrap().session_id == 'session_123'
        mock_payments_repository.get_pending_from.assert_called_once()
        mock_session_based_payment.create_checkout_session.assert_called_once()
        mock_payments_repository.create.assert_called_once()
        mock_payments_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()

    def test_successful_checkout_retrieves_existing_session(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        mock_payment,
    ):
        """Should retrieve existing checkout session when pending payment exists with session ID."""
        # Arrange
        mock_payment.gateway_payment_session_id = 'existing_session_123'

        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(mock_payment)

        session_result = CheckoutResultDTO.safe_create(
            client_id='client_123',
            session_id='existing_session_123',
            session_url='http://checkout.com',
        ).unwrap()
        mock_session_based_payment.retrieve_checkout_session.return_value = Result.Ok(
            session_result
        )

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_ok()
        assert result.unwrap().session_id == 'existing_session_123'
        mock_session_based_payment.retrieve_checkout_session.assert_called_once_with(
            'existing_session_123'
        )

    def test_checkout_creates_session_for_existing_payment_without_session_id(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        mock_payment,
    ):
        """Should create a new checkout session when a pending payment exists but has no session ID."""
        # Arrange
        mock_payment.gateway_payment_session_id = None

        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(mock_payment)

        session_result = CheckoutResultDTO.safe_create(
            client_id='client_123', session_id='new_session_123', session_url='http://checkout.com'
        ).unwrap()
        mock_session_based_payment.create_checkout_session.return_value = Result.Ok(
            session_result
        )
        mock_payments_repository.update.return_value = Result.Ok(mock_payment)

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_ok()
        assert result.unwrap().session_id == 'new_session_123'
        mock_session_based_payment.create_checkout_session.assert_called_once()
        mock_payments_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()

    def test_checkout_fails_when_client_not_found(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
    ):
        """Should return error when client is not found."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=999,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Err('Client not found')

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_err()
        assert 'Failed to find client' in result.unwrap_err().msg

    def test_checkout_fails_when_reservation_not_found(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
    ):
        """Should return error when reservation is not found."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=999,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(mocker.Mock())
        mock_reservation_repository.find_by_id.return_value = Result.Err('Reservation not found')

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_err()
        assert 'Failed to find reservation' in result.unwrap_err().msg

    def test_checkout_fails_when_session_creation_fails(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        mock_reservation,
        mock_payment,
    ):
        """Should rollback transaction and return error when checkout session creation fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(mocker.Mock())
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Ok(mock_payment)
        mock_session_based_payment.create_checkout_session.return_value = Result.Err('Session creation failed')

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_err()
        assert 'Failed to create payment session' in result.unwrap_err().msg
        mock_unit_of_work.rollback.assert_called_once()

    def test_checkout_fails_when_session_input_creation_fails(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        mock_reservation,
        mock_payment,
    ):
        """Should return error when CheckoutSessionInputDTO creation fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(mocker.Mock())
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Ok(mock_payment)

        mocker.patch(
            'payments.domain.dtos.CheckoutSessionInputDTO.safe_create',
            return_value=Result.Err('Invalid input'),
        )

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_err()
        assert 'Failed to create checkout session input' in result.unwrap_err().msg

    def test_checkout_fails_when_payment_creation_fails(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        mock_reservation,
        mock_payment,
    ):
        """Should rollback and return error when payment creation fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(mocker.Mock())
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Err('DB Error')

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_err()
        assert 'Failed to create payment' in result.unwrap_err().msg
        mock_unit_of_work.rollback.assert_called_once()

    def test_checkout_fails_when_payment_update_fails(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        mock_reservation,
        mock_payment,
    ):
        """Should rollback and return error when payment update fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=1,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(mocker.Mock())
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Ok(mock_payment)

        session_result = CheckoutResultDTO.safe_create(
            client_id='client_123', session_id='session_123', session_url='http://checkout.com'
        ).unwrap()
        mock_session_based_payment.create_checkout_session.return_value = Result.Ok(
            session_result
        )

        mock_payments_repository.update.return_value = Result.Err('Update failed')

        usecase = CheckoutUseCase(
            client_repo=mock_client_repository,
            payment_repo=mock_payments_repository,
            payment_gateway=mock_session_based_payment,
            reservation_repo=mock_reservation_repository,
            uow=mock_unit_of_work,
            logger=logger_mock,
        )

        # Act
        result = usecase(dto)

        # Assert
        assert result.is_err()
        assert 'Failed to update payment' in result.unwrap_err().msg
        mock_unit_of_work.rollback.assert_called_once()
