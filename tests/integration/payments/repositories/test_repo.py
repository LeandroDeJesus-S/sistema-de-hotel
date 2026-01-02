import pytest
from datetime import date, timedelta
from ddf import G
from exc import Result

from payments.domain.entities import PaymentGateway, PaymentStatus
from payments.infra.repo import PaymentRepository
from payments.models import Payment as PaymentModel


@pytest.mark.django_db
class TestPaymentRepository:
    def test_create_success(self):
        """Should successfully create a payment in the database."""
        # Arrange
        repo = PaymentRepository()
        # Create test data
        client = G('clients.Client')
        room = G('reservations.Room')
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = G(
            'reservations.Reservation',
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment_entity = G(
            'payments.domain.entities.Payment',
            client=client,
            reservation=reservation,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
        )

        # Act
        result = repo.create(payment_entity)

        # Assert
        assert result.is_ok()
        created_payment = result.unwrap()
        assert created_payment.id is not None
        assert created_payment.status == PaymentStatus.PENDING
        # Verify in DB
        db_payment = PaymentModel.objects.get(id=created_payment.id)
        assert db_payment.status == PaymentStatus.PENDING

    def test_create_entity_to_model_error(self, mocker):
        """Should return error when entity_to_model fails."""
        # Arrange
        repo = PaymentRepository()
        reservation = G('reservations.Reservation')
        client = reservation.client
        payment_entity = G(
            'payments.domain.entities.Payment',
            client=client,
            reservation=reservation,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
        )

        mocker.patch(
            'payments.infra.repo.entity_to_model', return_value=Result.Err('Conversion error')
        )

        # Act
        result = repo.create(payment_entity)

        # Assert
        assert result.is_err()
        assert 'Failed to convert payment entity to model' in result.unwrap_err().msg

    def test_create_model_to_entity_error(self, mocker):
        """Should return error when model_to_entity fails after save."""
        # Arrange
        repo = PaymentRepository()
        reservation = G('reservations.Reservation')
        client = reservation.client
        payment_entity = G(
            'payments.domain.entities.Payment',
            client=client,
            reservation=reservation,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
        )

        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Err('Conversion error')
        )

        # Act
        result = repo.create(payment_entity)

        # Assert
        assert result.is_err()
        assert (
            'Failed to convert created payment model back to entity' in result.unwrap_err().msg
        )

    def test_create_db_error(self, mocker):
        """Should return error when database save fails."""
        # Arrange
        repo = PaymentRepository()
        reservation = G('reservations.Reservation')
        client = reservation.client
        payment_entity = G(
            'payments.domain.entities.Payment',
            client=client,
            reservation=reservation,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
        )

        mock_model = mocker.Mock()
        mocker.patch('payments.infra.repo.entity_to_model', return_value=Result.Ok(mock_model))
        mock_model.save.side_effect = Exception('DB error')

        # Act
        result = repo.create(payment_entity)

        # Assert
        assert result.is_err()
        assert 'Failed to create payment in database' in result.unwrap_err().msg

    def test_get_by_reservation_id_success(self):
        """Should successfully retrieve payment by reservation ID."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel)

        # Act
        result = repo.get_by_reservation_id(payment.reservation.id)

        # Assert
        assert result.is_ok()
        retrieved_payment = result.unwrap()
        assert retrieved_payment.id == payment.id

    def test_get_by_reservation_id_not_found(self):
        """Should return error when payment not found for reservation."""
        # Arrange
        repo = PaymentRepository()

        # Act
        result = repo.get_by_reservation_id(99999)

        # Assert
        assert result.is_err()
        assert 'Payment not found for reservation' in result.unwrap_err().msg

    def test_get_by_reservation_id_conversion_error(self, mocker):
        """Should return error when model_to_entity fails."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel)

        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Err('Conversion error')
        )

        # Act
        result = repo.get_by_reservation_id(payment.reservation.id)

        # Assert
        assert result.is_err()
        assert 'Failed to convert payment model to entity' in result.unwrap_err().msg

    def test_get_by_reservation_id_db_error(self, mocker):
        """Should return error when database query fails."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel)

        mock_queryset = mocker.Mock()
        mock_queryset.first.side_effect = Exception('DB error')
        mocker.patch.object(PaymentModel.objects, 'filter', return_value=mock_queryset)

        # Act
        result = repo.get_by_reservation_id(payment.reservation.id)

        # Assert
        assert result.is_err()
        assert (
            f'Failed to get payment for reservation {payment.reservation.id}'
            in result.unwrap_err().msg
        )

    def test_get_by_gateway_session_id_success(self):
        """Should successfully retrieve payment by gateway session ID."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel, gateway_payment_session_id='session_123')

        # Act
        result = repo.get_by_gateway_session_id('session_123')

        # Assert
        assert result.is_ok()
        retrieved_payment = result.unwrap()
        assert retrieved_payment.gateway_payment_session_id == 'session_123'

    def test_get_by_gateway_session_id_not_found(self):
        """Should return error when payment not found for session ID."""
        # Arrange
        repo = PaymentRepository()

        # Act
        result = repo.get_by_gateway_session_id('nonexistent_session')

        # Assert
        assert result.is_err()
        assert 'Payment not found for session' in result.unwrap_err().msg

    def test_get_by_gateway_payment_intent_id_success(self):
        """Should successfully retrieve payment by gateway payment intent ID."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel, gateway_payment_intent_id='pi_123')

        # Act
        result = repo.get_by_gateway_payment_intent_id('pi_123')

        # Assert
        assert result.is_ok()
        retrieved_payment = result.unwrap()
        assert retrieved_payment.gateway_payment_intent_id == 'pi_123'

    def test_get_by_gateway_payment_intent_id_not_found(self):
        """Should return error when payment not found for payment intent ID."""
        # Arrange
        repo = PaymentRepository()

        # Act
        result = repo.get_by_gateway_payment_intent_id('nonexistent_pi')

        # Assert
        assert result.is_err()
        assert 'Payment not found for payment intent' in result.unwrap_err().msg

    def test_update_success(self):
        """Should successfully update a payment in the database."""
        # Arrange
        repo = PaymentRepository()
        payment_model = G(PaymentModel)
        from utils.support import model_to_entity
        from payments.domain.entities import Payment

        entity_result = model_to_entity(payment_model, Payment)
        assert entity_result.is_ok()
        payment_entity = entity_result.unwrap()
        payment_entity.status = PaymentStatus.COMPLETED

        # Act
        result = repo.update(payment_entity)

        # Assert
        assert result.is_ok()
        updated_payment = result.unwrap()
        assert updated_payment.status == PaymentStatus.COMPLETED
        # Verify in DB
        db_payment = PaymentModel.objects.get(id=payment_entity.id)
        assert db_payment.status == PaymentStatus.COMPLETED

    def test_update_entity_to_model_error(self, mocker):
        """Should return error when entity_to_model fails for update."""
        # Arrange
        repo = PaymentRepository()
        payment_model = G(PaymentModel)
        from utils.support import model_to_entity
        from payments.domain.entities import Payment

        entity_result = model_to_entity(payment_model, Payment)
        assert entity_result.is_ok()
        payment_entity = entity_result.unwrap()

        mocker.patch(
            'payments.infra.repo.entity_to_model', return_value=Result.Err('Conversion error')
        )

        # Act
        result = repo.update(payment_entity)

        # Assert
        assert result.is_err()
        assert (
            'Failed to convert payment entity to model for update' in result.unwrap_err().msg
        )

    def test_update_db_error(self, mocker):
        """Should return error when database update fails."""
        # Arrange
        repo = PaymentRepository()
        payment_model = G(PaymentModel)
        from utils.support import model_to_entity
        from payments.domain.entities import Payment

        entity_result = model_to_entity(payment_model, Payment)
        assert entity_result.is_ok()
        payment_entity = entity_result.unwrap()

        mock_model = mocker.Mock()
        mocker.patch('payments.infra.repo.entity_to_model', return_value=Result.Ok(mock_model))
        mock_model.save.side_effect = Exception('DB error')

        # Act
        result = repo.update(payment_entity)

        # Assert
        assert result.is_err()
        assert f'Failed to update payment {payment_entity.id}' in result.unwrap_err().msg

    def test_get_by_id_success(self):
        """Should successfully retrieve payment by ID."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel)

        # Act
        result = repo.get_by_id(payment.id)

        # Assert
        assert result.is_ok()
        retrieved_payment = result.unwrap()
        assert retrieved_payment.id == payment.id

    def test_get_by_id_not_found(self):
        """Should return error when payment not found by ID."""
        # Arrange
        repo = PaymentRepository()

        # Act
        result = repo.get_by_id(99999)

        # Assert
        assert result.is_err()
        assert 'Payment not found' in result.unwrap_err().msg

    def test_get_pending_from_success(self):
        """Should successfully retrieve pending payment by reservation ID."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel, status=PaymentModel.Status.PENDING)

        # Act
        result = repo.get_pending_from(payment.reservation.id)

        # Assert
        assert result.is_ok()
        retrieved_payment = result.unwrap()
        assert retrieved_payment.status == PaymentStatus.PENDING

    def test_get_pending_from_not_found(self):
        """Should return error when no pending payment found for reservation."""
        # Arrange
        repo = PaymentRepository()
        payment = G(PaymentModel, status=PaymentModel.Status.PAID)

        # Act
        result = repo.get_pending_from(payment.reservation.id)

        # Assert
        assert result.is_err()
        assert 'Payment not found' in result.unwrap_err().msg
