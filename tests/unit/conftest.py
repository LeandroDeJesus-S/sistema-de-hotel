import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
from ddf import G

from django.core.management import call_command

from clients.models import Client
from home.models import Hotel, Contact
from payments.models import Payment
from reservations.models import Benefit, Class, Reservation, Room
from reservations.rules import RoomRules
from schedules.models import Scheduling
from services.models import Service


@pytest.fixture(scope='function', autouse=True)
def auth_backend(settings):
    """Use the custom authentication backend for tests."""
    settings.AUTHENTICATION_BACKENDS = ['clients.authenticator.UserEmailAuthBackend']
    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


@pytest.fixture(scope='session', autouse=True)
def faker_session_locale():
    return ['pt_BR']


@pytest.fixture(scope='function')
def valid_client_data_factory(faker):
    """
    Provides a dictionary with valid data for creating a Client instance.
    """
    def f():
        first_name = re.sub(r'[^a-zA-Z]', '', faker.first_name().split(' ')[0])
        last_name = re.sub(r'[^a-zA-Z]', '', faker.last_name().split(' ')[0])
        return {
            'username': faker.user_name(),
            'password': faker.password(
                length=12, special_chars=True, digits=True, upper_case=True, lower_case=True
            ),
            'first_name': first_name,
            'last_name': last_name,
            'birthdate': faker.date_of_birth(minimum_age=18, maximum_age=80),
            'email': faker.email(),
            'phone': faker.phone_number(),
            'cpf': faker.cpf().replace('.', '').replace('-', ''),
        }
    return f

@pytest.fixture
def client_model_factory(db, valid_client_data_factory, monkeypatch):
    def f():
        valid_client_data = valid_client_data_factory()
        u = G(Client, **valid_client_data)
        u.set_password(valid_client_data['password'])
        u.save()
        monkeypatch.setattr(u, 'raw_password', valid_client_data['password'], raising=False)
        return u
    return f

@pytest.fixture(scope='function')
def client_model(db, valid_client_data_factory, monkeypatch):
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
def authenticated_client(client, client_model):
    """
    Logs in a client and returns the client and user.
    """
    client.force_login(client_model)
    return client, client_model


@pytest.fixture
def mock_recaptcha(responses):
    responses.add(
        responses.POST,
        'https://www.google.com/recaptcha/api/siteverify',
        json={'success': True, 'score': 0.9},
        status=200,
    )

@pytest.fixture
def hotel_model(db):
    """
    Fixture to create a Hotel instance.
    """
    return G(Hotel)


@pytest.fixture
def contact_model(db, hotel_model):
    """
    Fixture to create a Contact instance.
    """
    return G(Contact, hotel=hotel_model)


@pytest.fixture
def benefit_model(db):
    """
    Fixture to create a Benefit instance for a room.
    """
    benefit, _ = Benefit.objects.get_or_create(
        name="Wi-Fi Grátis",
        defaults={'short_desc': "Acesso à internet de alta velocidade em todo o hotel."}
    )
    return benefit


@pytest.fixture
def room_class_model(db):
    """
    Fixture to create a Class instance for a room.
    """
    room_class, _ = Class.objects.get_or_create(name="Standard")
    return room_class


@pytest.fixture
def room_model(db, room_class_model, benefit_model, hotel_model, faker):
    """
    Fixture to create a Room instance with associated class, benefit, and hotel.
    Set a daily_price that ensures reservation amount is valid.
    """
    room = G(
        Room,
        number=faker.bothify("###?"),
        room_class=room_class_model,
        hotel=hotel_model,
        daily_price=Decimal("200.00"),
        size=faker.pyint(min_value=RoomRules.MIN_SIZE + 1, max_value=RoomRules.MAX_SIZE - 1),
        short_desc=faker.sentence(nb_words=5),
        adults_capacity=faker.pyint(min_value=RoomRules.MIN_ADULTS, max_value=RoomRules.MAX_ADULTS),
        children_capacity=faker.pyint(min_value=RoomRules.MIN_CHILDREN, max_value=RoomRules.MAX_CHILDREN),
    )
    room.benefits.add(benefit_model)
    return room


@pytest.fixture
def reservation_model(db, client_model, room_model):
    """
    Fixture to create a Reservation instance.
    """
    checkin = date.today() + timedelta(days=10)
    checkout = checkin + timedelta(days=15)  # Example: 5 days reservation
    reservation = G(
        Reservation,
        client=client_model,
        room=room_model,
        checkin=checkin,
        checkout=checkout,
        status="I",
    )
    # Calculate and set the amount
    reservation.amount = reservation.calc_reservation_value()
    reservation.save()  # Save after setting amount
    return reservation


@pytest.fixture
def payment_model(db, reservation_model, contact_model):
    """
    Fixture to create a Payment instance.
    """
    return G(
        Payment, 
        reservation=reservation_model, 
        status="P", 
        amount=reservation_model.amount, 
    )


@pytest.fixture
def scheduling_model(db, client_model, reservation_model):
    """
    Fixture to create a Scheduling instance.
    """
    return G(Scheduling, client=client_model, reservation=reservation_model)


@pytest.fixture
def service_model(db, hotel_model):
    """
    Fixture to create a Service instance.
    """
    return G(Service, hotel=hotel_model)

@pytest.fixture
def db_setup(db):
    """
    Loads the necessary fixtures for the unit tests.
    """
    call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
    call_command('loaddata', 'tests/fixtures/servico_fixture.json')
    call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
    call_command('loaddata', 'tests/fixtures/classe_fixture.json')
    call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
    call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
    call_command('loaddata', 'tests/fixtures/reserva_fixture.json')
