import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from ddf import G
from django.utils import timezone
from exc import Result
from reservations.models import Reservation

from payments.domain.entities import Payment, PaymentGateway, PaymentStatus
from payments.infra.repo import PaymentRepository
from payments.models import Payment as PaymentModel


@pytest.mark.django_db
class TestPaymentRepository:
    def test_create_success(self):
        """Should successfully create a payment in the database."""
        # Arrange
        repo = PaymentRepository()
        # Create test data
        from datetime import date
        from reservations.models import Reservation

        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser',
            first_name='John',
            last_name='Doe',
            phone='123456789012',
            cpf='12345678901',
            email='test@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='101', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        # Convert to domain entities
        from utils.support import model_to_entity
        from reservations.domain.entities import Reservation
        from clients.domain.entities import Client

        client_entity = model_to_entity(client, Client).unwrap()
        reservation_entity = model_to_entity(reservation, Reservation).unwrap()
        payment_entity = Payment(
            id=None,
            client=client_entity,
            reservation=reservation_entity,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            gateway_payment_session_id=None,
            gateway_payment_intent_id=None,
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        # Convert to domain entities
        from utils.support import model_to_entity
        from reservations.domain.entities import Reservation
        from clients.domain.entities import Client

        client_entity = model_to_entity(client, Client).unwrap()
        reservation_entity = model_to_entity(reservation, Reservation).unwrap()
        payment_entity = Payment(
            id=None,
            client=client_entity,
            reservation=reservation_entity,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            gateway_payment_session_id=None,
            gateway_payment_intent_id=None,
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
        from datetime import date
        from reservations.models import Reservation

        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser',
            first_name='John',
            last_name='Doe',
            phone='123456789012',
            cpf='12345678901',
            email='test@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='101', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        # Convert to domain entities
        from utils.support import model_to_entity
        from reservations.domain.entities import Reservation
        from clients.domain.entities import Client

        client_entity = model_to_entity(client, Client).unwrap()
        reservation_entity = model_to_entity(reservation, Reservation).unwrap()
        payment_entity = Payment(
            id=None,
            client=client_entity,
            reservation=reservation_entity,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            gateway_payment_session_id=None,
            gateway_payment_intent_id=None,
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
        from datetime import date
        from reservations.models import Reservation

        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser',
            first_name='John',
            last_name='Doe',
            phone='123456789012',
            cpf='12345678901',
            email='test@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='101', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        # Convert to domain entities
        from utils.support import model_to_entity
        from reservations.domain.entities import Reservation
        from clients.domain.entities import Client

        client_entity = model_to_entity(client, Client).unwrap()
        reservation_entity = model_to_entity(reservation, Reservation).unwrap()
        payment_entity = Payment(
            id=None,
            client=client_entity,
            reservation=reservation_entity,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            gateway_payment_session_id=None,
            gateway_payment_intent_id=None,
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
        from datetime import date
        from reservations.models import Reservation

        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser',
            first_name='John',
            last_name='Doe',
            phone='123456789012',
            cpf='12345678901',
            email='test@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='101', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        # Convert to domain entities
        from utils.support import model_to_entity
        from reservations.domain.entities import Reservation
        from clients.domain.entities import Client

        client_entity = model_to_entity(client, Client).unwrap()
        reservation_entity = model_to_entity(reservation, Reservation).unwrap()
        payment_entity = Payment(
            id=None,
            client=client_entity,
            reservation=reservation_entity,
            amount=reservation.amount,
            status=PaymentStatus.PENDING,
            payment_gateway=PaymentGateway.STRIPE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            gateway_payment_session_id=None,
            gateway_payment_intent_id=None,
        )

        mock_model = mocker.Mock()
        mocker.patch('payments.infra.repo.entity_to_model', return_value=Result.Ok(mock_model))
        mock_model.save.side_effect = Exception('DB error')

        # Act
        result = repo.create(payment_entity)

        # Assert
        assert result.is_err()
        assert 'Failed to create payment in database' in result.unwrap_err().msg

    def test_get_by_reservation_id_success(self, mocker):
        """Should successfully retrieve payment by reservation ID."""
        # Arrange
        repo = PaymentRepository()
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser2',
            first_name='Jane',
            last_name='Doe',
            phone='123456789013',
            cpf='12345678902',
            password='password123',
        )
        room = G('reservations.Room', number='102', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment = G(PaymentModel, reservation=reservation)

        mock_payment_entity = mocker.Mock()
        mock_payment_entity.id = payment.id
        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Ok(mock_payment_entity)
        )

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
        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Err('Conversion error')
        )
        """Should return error when model_to_entity fails."""
        # Arrange
        repo = PaymentRepository()
        client = G('clients.Client')
        client.birthdate = date(1990, 1, 1)
        client.username = 'testuser4'
        client.first_name = 'Bob'
        client.last_name = 'Doe'
        client.phone = '123456789015'
        client.cpf = '12345678904'
        client.save()
        room = G('reservations.Room', number='104', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment = G(PaymentModel, reservation=reservation)

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
        client = G('clients.Client')
        client.birthdate = date(1990, 1, 1)
        client.username = 'testuser4'
        client.first_name = 'Bob'
        client.last_name = 'Doe'
        client.phone = '123456789015'
        client.cpf = '12345678904'
        client.save()
        room = G('reservations.Room', number='104', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment = G(PaymentModel, reservation=reservation)

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

    def test_get_by_gateway_session_id_success(self, mocker):
        """Should successfully retrieve payment by gateway session ID."""
        # Arrange
        repo = PaymentRepository()
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser6',
            first_name='Alice',
            last_name='Smith',
            phone='123456789016',
            cpf='12345678906',
            email='test6@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='106', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment = PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.PENDING,
            gateway_payment_session_id='session_123',
        )

        mock_payment_entity = mocker.Mock()
        mock_payment_entity.gateway_payment_session_id = 'session_123'
        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Ok(mock_payment_entity)
        )

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

    def test_get_by_gateway_payment_intent_id_success(self, mocker):
        """Should successfully retrieve payment by gateway payment intent ID."""
        # Arrange
        repo = PaymentRepository()
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser5',
            first_name='Charlie',
            last_name='Davis',
            phone='123456789015',
            cpf='12345678905',
            email='test5@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='105', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment = PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.PENDING,
            gateway_payment_intent_id='pi_123',
        )

        mock_payment_entity = mocker.Mock()
        mock_payment_entity.gateway_payment_intent_id = 'pi_123'
        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Ok(mock_payment_entity)
        )

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
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser8',
            first_name='Eve',
            last_name='Brown',
            phone='123456789018',
            cpf='12345678908',
            email='test8@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='108', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment_model = PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.PENDING,
        )
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
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser11',
            first_name='Helen',
            last_name='Foster',
            phone='123456789021',
            cpf='12345678911',
            email='test11@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='111', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment_model = PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.PENDING,
        )
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
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser11',
            first_name='Helen',
            last_name='Foster',
            phone='123456789021',
            cpf='12345678911',
            email='test11@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='111', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment_model = PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.PENDING,
        )
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

    def test_get_by_id_success(self, mocker):
        """Should successfully retrieve payment by ID."""
        # Arrange
        repo = PaymentRepository()
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser7',
            first_name='Bob',
            last_name='Johnson',
            phone='123456789017',
            cpf='12345678907',
            email='test7@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='107', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment = PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.PENDING,
        )

        mock_payment_entity = mocker.Mock()
        mock_payment_entity.id = payment.id
        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Ok(mock_payment_entity)
        )

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

    def test_get_pending_from_success(self, mocker):
        """Should successfully retrieve pending payment by reservation ID."""
        # Arrange
        repo = PaymentRepository()
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser9',
            first_name='Frank',
            last_name='White',
            phone='123456789019',
            cpf='12345678909',
            email='test9@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='109', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        payment = PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.PENDING,
        )

        mock_payment_entity = mocker.Mock()
        mock_payment_entity.status = PaymentStatus.PENDING
        mocker.patch(
            'payments.infra.repo.model_to_entity', return_value=Result.Ok(mock_payment_entity)
        )

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
        from clients.models import Client

        client = Client.objects.create(
            birthdate=date(1990, 1, 1),
            username='testuser10',
            first_name='Grace',
            last_name='Black',
            phone='123456789020',
            cpf='12345678910',
            email='test10@example.com',
            password='password123',
        )
        room = G('reservations.Room', number='110', size=20.0, daily_price=Decimal('200.00'))
        checkin = date.today() + timedelta(days=1)
        checkout = checkin + timedelta(days=5)
        reservation = Reservation.objects.create(
            client=client,
            room=room,
            checkin=checkin,
            checkout=checkout,
            amount=Decimal('0.00'),
            status='I',
        )
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()
        PaymentModel.objects.create(
            reservation=reservation,
            amount=reservation.amount,
            client=client,
            payment_gateway=PaymentModel.Gateway.STRIPE,
            status=PaymentModel.Status.COMPLETED,  # Not pending
        )

        # Act
        result = repo.get_pending_from(reservation.id)

        # Assert
        assert result.is_err()
        assert 'Payment not found' in result.unwrap_err().msg
