import logging
import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
from ddf import G
from faker import Faker

from base.ports.email import AbsEmailSender
from base.ports.pdf import AbsPDFGenerator
from base.ports.unit_of_work import AbsUnitOfWork
from clients.domain.ports import AbsClientRepository
from clients.models import Client
from clients.rules import ClientRules
from home.models import Contact, Hotel
from payments.models import Payment
from reservations.domain.repo import AbsReservationRepository, AbsRoomRepository
from reservations.models import Benefit, Class, Reservation, Room
from reservations.rules import RoomRules
from services.models import Service


@pytest.fixture(scope='function', autouse=True)
def auth_backend(settings):
    """Use the custom authentication backend for tests."""
    settings.AUTHENTICATION_BACKENDS = ['clients.authenticator.UserEmailAuthBackend']
    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


@pytest.fixture(scope='session', autouse=False)
def faker():
    return Faker(locale='pt_BR')


@pytest.fixture(scope='function')
def valid_client_data_factory(faker):
    """
    Provides a dictionary with valid data for creating a Client instance.
    """

    def f():
        first_name = re.sub(r'[^a-zA-Z]', '', faker.first_name().split(' ')[0])
        last_name = re.sub(r'[^a-zA-Z ]', '', faker.last_name())
        if len(last_name) < ClientRules.MIN_SURNAME_CHARS:
            last_name = last_name.ljust(ClientRules.MIN_SURNAME_CHARS, 'a')

        return {
            'username': faker.user_name(),
            'password': faker.password(
                length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
            ),
            'first_name': first_name,
            'last_name': last_name,
            'birthdate': faker.date_of_birth(minimum_age=18, maximum_age=80),
            'email': faker.email(),
            'phone': faker.numerify('(%%) 9####-####'),
            'cpf': faker.cpf().replace('.', '').replace('-', ''),
        }

    return f


@pytest.fixture
def client_model_instance_factory(db, valid_client_data_factory, monkeypatch):
    """Returns a function that creates a valid client instance."""

    def f():
        valid_client_data = valid_client_data_factory()
        u = G(Client, **valid_client_data)
        u.set_password(valid_client_data['password'])
        u.save()
        monkeypatch.setattr(u, 'raw_password', valid_client_data['password'], raising=False)
        return u

    return f


@pytest.fixture(scope='function')
def client_model_instance(db, valid_client_data_factory, monkeypatch):
    """
    Provides a valid client instance.
    """
    valid_client_data = valid_client_data_factory()
    u = G(Client, **valid_client_data)
    u.set_password(valid_client_data['password'])
    u.save()
    monkeypatch.setattr(u, 'raw_password', valid_client_data['password'], raising=False)
    return u


@pytest.fixture(scope='function')
def authenticated_client(client, client_model_instance):
    """
    Logs in a client and returns a tuple with the http client and user.
    """
    client.force_login(client_model_instance)
    return client, client_model_instance


@pytest.fixture
def mock_recaptcha(responses):
    responses.add(
        responses.POST,
        'https://www.google.com/recaptcha/api/siteverify',
        json={'success': True, 'score': 0.9},
        status=200,
    )


@pytest.fixture
def hotel_model_instance(db):
    """
    Fixture to create a Hotel instance.
    """
    return G(Hotel)


@pytest.fixture
def contact_model_instance(db, hotel_model_instance):
    """
    Fixture to create a Contact instance.
    """
    return G(Contact, hotel=hotel_model_instance)


@pytest.fixture
def benefit_model_instance(db):
    """
    Fixture to create a Benefit instance for a room.
    """
    benefit, _ = Benefit.objects.get_or_create(
        name='Wi-Fi Grátis',
        defaults={'short_desc': 'Acesso à internet de alta velocidade em todo o hotel.'},
    )
    return benefit


@pytest.fixture
def room_class_model_instance(db):
    """
    Fixture to create a Class instance for a room.
    """
    room_class, _ = Class.objects.get_or_create(name='Standard')
    return room_class


@pytest.fixture
def room_model_instance(
    db, room_class_model_instance, benefit_model_instance, hotel_model_instance, faker
):
    """
    Fixture to create a Room instance with associated class, benefit, and hotel.
    Set a daily_price that ensures reservation amount is valid.
    """
    import string
    room = G(
        Room,
        number=faker.bothify('###') + faker.random_element(string.ascii_uppercase),
        room_class=room_class_model_instance,
        hotel=hotel_model_instance,
        daily_price=Decimal('200.00'),
        size=faker.pyint(min_value=RoomRules.MIN_SIZE + 1, max_value=RoomRules.MAX_SIZE - 1),
        short_desc=faker.sentence(nb_words=5),
        adults_capacity=faker.pyint(
            min_value=RoomRules.MIN_ADULTS, max_value=RoomRules.MAX_ADULTS
        ),
        children_capacity=faker.pyint(
            min_value=RoomRules.MIN_CHILDREN, max_value=RoomRules.MAX_CHILDREN
        ),
    )
    room.benefits.add(benefit_model_instance)
    return room


@pytest.fixture
def reservation_model_instance(db, client_model_instance, room_model_instance):
    """
    Fixture to create a Reservation instance.
    """
    checkin = date.today() + timedelta(days=10)
    checkout = checkin + timedelta(days=15)  # Example: 5 days reservation
    reservation = G(
        Reservation,
        client=client_model_instance,
        room=room_model_instance,
        checkin=checkin,
        checkout=checkout,
        status='I',
    )
    # Calculate and set the amount
    reservation.amount = reservation.calc_reservation_value()
    reservation.save()  # Save after setting amount
    return reservation


@pytest.fixture
def reservation_model_instance_factory(db, client_model_instance, room_model_instance):
    """
    Fixture to create Reservation instances via a factory.
    """

    def f(client=None, room=None, status='I'):
        checkin = date.today() + timedelta(days=10)
        checkout = checkin + timedelta(days=15)  # Example: 5 days reservation
        reservation = G(
            Reservation,
            client=client if client else client_model_instance,
            room=room if room else room_model_instance,
            checkin=checkin,
            checkout=checkout,
            status=status,
        )
        # Calculate and set the amount
        reservation.amount = reservation.calc_reservation_value()
        reservation.save()  # Save after setting amount
        return reservation

    return f


@pytest.fixture
def payment_model_instance(db, reservation_model_instance):
    """
    Fixture to create a Payment instance.
    """
    return G(
        Payment,
        reservation=reservation_model_instance,
        status=Payment.Status.PENDING,
        amount=reservation_model_instance.amount,
        client=reservation_model_instance.client,
        payment_gateway=Payment.Gateway.STRIPE,
    )


@pytest.fixture
def service_model_instance(db, hotel_model_instance):
    """
    Fixture to create a Service instance.
    """
    return G(Service, hotel=hotel_model_instance)


@pytest.fixture
def reservations_container(settings):
    from reservations.container import ReservationsContainer  # noqa: PLC0415

    reservations_container = ReservationsContainer()
    reservations_container.config.from_dict(settings.__dict__)
    reservations_container.wire(modules=['reservations.views', 'reservations.infra.tasks'])
    return reservations_container


@pytest.fixture
def payments_container(settings):
    from payments.container import PaymentsContainer  # noqa: PLC0415

    payments_container = PaymentsContainer()
    payments_container.config.from_dict(settings.__dict__)
    payments_container.wire(modules=['payments.views', 'payments.infra.tasks'])
    return payments_container


@pytest.fixture
def clients_container(settings):
    from clients.container import ClientsContainer  # noqa: PLC0415

    clients_container = ClientsContainer()
    clients_container.config.from_dict(settings.__dict__)
    clients_container.wire(modules=['clients.views'])


@pytest.fixture
def mock_client_repository(mocker):
    """Mock fixture for AbsClientRepository port (shared across apps)."""
    return mocker.Mock(spec=AbsClientRepository)


@pytest.fixture
def mock_reservation_repository(mocker):
    """Mock fixture for AbsReservationRepository port (shared across apps)."""
    return mocker.Mock(spec=AbsReservationRepository)


@pytest.fixture
def mock_room_repository(mocker):
    """Mock fixture for AbsRoomRepository port (shared across apps)."""
    return mocker.Mock(spec=AbsRoomRepository)


@pytest.fixture
def mock_email_sender(mocker):
    """Mock fixture for AbsEmailSender port."""
    return mocker.Mock(spec=AbsEmailSender)


@pytest.fixture
def mock_pdf_generator(mocker):
    """Mock fixture for AbsPDFGenerator port."""
    return mocker.Mock(spec=AbsPDFGenerator)


@pytest.fixture
def mock_unit_of_work(mocker):
    """Mock fixture for AbsUnitOfWork port."""
    mock = mocker.MagicMock(spec=AbsUnitOfWork)
    return mock


@pytest.fixture
def logger_mock(mocker):
    return mocker.Mock(spec=logging.Logger)
