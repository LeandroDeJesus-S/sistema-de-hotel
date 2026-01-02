import pytest

from clients.domain.entities import Client
from home.domain.entities import Hotel
from reservations.domain.entities import Benefit, Room, RoomClass


@pytest.fixture
def hotel_fixture(faker):
    return Hotel(
        name=faker.company(),
        slogan=faker.catch_phrase(),
        presentation_text=faker.text(),
        address=faker.address(),
        phone=faker.phone_number(),
        email=faker.email(),
        website=faker.url(),
    )


@pytest.fixture
def room_class_fixture():
    return RoomClass(name='Deluxe')


@pytest.fixture
def benefits_fixture():
    return [
        Benefit(name='Wi-Fi', icon='wifi.svg', short_desc='Free Wi-Fi'),
        Benefit(name='TV', icon='tv.svg', short_desc='Flat screen TV'),
    ]


@pytest.fixture
def client_fixture(faker):
    return Client(
        username=faker.user_name(),
        first_name=faker.first_name(),
        last_name=faker.last_name(),
        birthdate=faker.date_of_birth(minimum_age=18),
        email=faker.email(),
        phone=faker.phone_number(),
        cpf=faker.ssn(),
        password=faker.password(),
    )


@pytest.fixture
def room_fixture(hotel_fixture, room_class_fixture, benefits_fixture):
    return Room(
        number='101',
        adults_capacity=2,
        children_capacity=1,
        size=25,
        daily_price=150.00,
        image='room.jpg',
        short_desc='A cozy room',
        long_desc='A very cozy room with a view',
        hotel=hotel_fixture,
        room_class=room_class_fixture,
        benefits=benefits_fixture,
    )
