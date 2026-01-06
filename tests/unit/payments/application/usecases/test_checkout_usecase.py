import pytest
from exc import Result

from payments.application.dtos import CheckoutUseCaseInputDTO
from payments.application.usecases import CheckoutUseCase
from payments.domain.dtos import CheckoutResultDTO, CheckoutSessionInputDTO
from payments.domain.entities import PaymentGateway, PaymentStatus

# For tests, remove the need for safe_create by using direct instantiation if possible, but since it's BaseEntity, use safe_create


class TestCheckoutUseCase:
    def test_successful_checkout_creates_new_payment_and_session(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        client_model_instance,
        reservation_model_instance,
    ):
        """Should create a new payment and checkout session when no pending payment exists."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=client_model_instance.id,
            reservation_id=reservation_model_instance.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(client_model_instance)
        mock_reservation = mocker.Mock()
        mock_reservation.reservation_days.return_value = Result.Ok(5)
        mock_reservation.room.daily_price = 200.00
        mock_reservation.amount = 1000.00
        mock_reservation.id = reservation_model_instance.id
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)
        session_result = CheckoutResultDTO.safe_create(
            client_id='client_123', session_id='session_123', session_url='http://checkout.com'
        ).unwrap()
        mock_session_based_payment.create_checkout_session.return_value = Result.Ok(
            session_result
        )
        mock_payment = mocker.Mock()
        mock_payment.id = 1
        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Ok(mock_payment)
        mock_payments_repository.update.return_value = Result.Ok(None)
        mock_unit_of_work.__enter__.return_value = mock_unit_of_work
        mock_unit_of_work.__exit__.return_value = None

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
        mock_payments_repository.get_pending_from.assert_called_once_with(dto.reservation_id)
        mock_client_repository.get_by_id.assert_called_once_with(dto.client_id)
        mock_reservation_repository.find_by_id.assert_called_once_with(dto.reservation_id)
        mock_session_based_payment.create_checkout_session.assert_called_once()
        mock_payments_repository.create.assert_called_once()
        mock_payments_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()

    def test_successful_checkout_retrieves_existing_session(
        self,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        payment_model_instance,
    ):
        """Should retrieve existing checkout session when pending payment exists."""
        # Arrange
        payment_model_instance.gateway_payment_session_id = 'existing_session_123'
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=payment_model_instance.reservation.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(
            payment_model_instance
        )
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

    def test_checkout_fails_when_client_not_found(
        self,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        reservation_model_instance,
    ):
        """Should return error when client is not found."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=999,
            reservation_id=reservation_model_instance.id,
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
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        client_model_instance,
    ):
        """Should return error when reservation is not found."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=client_model_instance.id,
            reservation_id=999,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(client_model_instance)
        mock_reservation_repository.find_by_id.return_value = Result.Err(
            'Reservation not found'
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
        client_model_instance,
        reservation_model_instance,
    ):
        """Should rollback transaction and return error when checkout session creation fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=client_model_instance.id,
            reservation_id=reservation_model_instance.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(client_model_instance)
        mock_reservation = mocker.Mock()
        mock_reservation.reservation_days.return_value = Result.Ok(5)
        mock_reservation.room.daily_price = 200.00
        mock_reservation.amount = 1000.00
        mock_reservation.id = reservation_model_instance.id
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)
        mock_payment = mocker.Mock()
        mock_payment.id = 1
        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Ok(mock_payment)
        mock_session_based_payment.create_checkout_session.return_value = Result.Err(
            'Session creation failed'
        )
        mock_unit_of_work.__enter__.return_value = mock_unit_of_work
        mock_unit_of_work.__exit__.return_value = None

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
        logger_mock.error.assert_called_once()

    def test_checkout_fails_when_existing_payment_has_no_session_id(
        self,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        payment_model_instance,
    ):
        """Should return error when existing payment has no session ID."""
        # Arrange
        payment_model_instance.gateway_payment_session_id = None
        dto = CheckoutUseCaseInputDTO(
            client_id=1,
            reservation_id=payment_model_instance.reservation.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(
            payment_model_instance
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
        assert 'payment session ID not found' in result.unwrap_err().msg

    def test_checkout_fails_when_session_input_creation_fails(
        self,
        mocker,
        mock_client_repository,
        mock_payments_repository,
        mock_session_based_payment,
        mock_reservation_repository,
        mock_unit_of_work,
        logger_mock,
        client_model_instance,
        reservation_model_instance,
    ):
        """Should return error when CheckoutSessionInputDTO creation fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=client_model_instance.id,
            reservation_id=reservation_model_instance.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(client_model_instance)

        mock_reservation = mocker.Mock()
        mock_reservation.reservation_days.return_value = Result.Ok(5)
        mock_reservation.room.daily_price = 200.00
        mock_reservation.amount = 1000.00
        mock_reservation.id = reservation_model_instance.id
        mock_reservation.room.number = '101'
        mock_reservation.room.room_class.name = 'Standard'
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

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
        client_model_instance,
        reservation_model_instance,
    ):
        """Should rollback and return error when payment creation fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=client_model_instance.id,
            reservation_id=reservation_model_instance.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(client_model_instance)

        mock_reservation = mocker.Mock()
        mock_reservation.reservation_days.return_value = Result.Ok(5)
        mock_reservation.room.daily_price = 200.00
        mock_reservation.amount = 1000.00
        mock_reservation.id = reservation_model_instance.id
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

        # Mock safe_create to return success (entity), but then repo.create to fail
        mock_payment = mocker.Mock()
        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Err('DB Error')

        mock_unit_of_work.__enter__.return_value = mock_unit_of_work
        mock_unit_of_work.__exit__.return_value = None

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
        client_model_instance,
        reservation_model_instance,
    ):
        """Should rollback and return error when payment update fails."""
        # Arrange
        dto = CheckoutUseCaseInputDTO(
            client_id=client_model_instance.id,
            reservation_id=reservation_model_instance.id,
            success_url='http://success.com',
            cancel_url='http://cancel.com',
        )
        mock_payments_repository.get_pending_from.return_value = Result.Ok(None)
        mock_client_repository.get_by_id.return_value = Result.Ok(client_model_instance)

        mock_reservation = mocker.Mock()
        mock_reservation.reservation_days.return_value = Result.Ok(5)
        mock_reservation.room.daily_price = 200.00
        mock_reservation.amount = 1000.00
        mock_reservation.id = reservation_model_instance.id
        mock_reservation_repository.find_by_id.return_value = Result.Ok(mock_reservation)

        mock_payment = mocker.Mock()
        mock_payment.id = 1
        mocker.patch(
            'payments.application.usecases.Payment.safe_create',
            return_value=Result.Ok(mock_payment),
        )
        mock_payments_repository.create.return_value = Result.Ok(mock_payment)

        # Session creation success
        session_result = CheckoutResultDTO.safe_create(
            client_id='client_123', session_id='session_123', session_url='http://checkout.com'
        ).unwrap()
        mock_session_based_payment.create_checkout_session.return_value = Result.Ok(session_result)

        # Update fails
        mock_payments_repository.update.return_value = Result.Err('Update failed')

        mock_unit_of_work.__enter__.return_value = mock_unit_of_work
        mock_unit_of_work.__exit__.return_value = None

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
