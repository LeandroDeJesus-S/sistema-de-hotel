import pytest
from clients.domain.entities import Client
from home.domain.entities import Hotel
from reservations.domain.entities import Benefit, Price, RoomClass, Room
from reservations.domain.value_objects import Currency, PriceValue


@pytest.fixture
def client_entity(valid_client_data_factory):
    data = valid_client_data_factory()
    return Client.safe_create(**data).unwrap()


@pytest.fixture
def hotel_entity():
    return Hotel.safe_create(
        name='Hotel California',
        slogan='Such a lovely place',
        presentation_text='Welcome to the Hotel California',
    ).unwrap()


@pytest.fixture
def room_class_entity():
    return RoomClass.safe_create(name='Suite').unwrap()


@pytest.fixture
def benefit_entity():
    return Benefit.safe_create(
        name='WiFi', icon='wifi.png', short_desc='Fast internet'
    ).unwrap()


@pytest.fixture
def price_entity():
    return Price.safe_create(
        currency=Currency.USD,
        value=20000,  # $200.00 in cents
        active=True,
    ).unwrap()


@pytest.fixture
def room_entity(hotel_entity, room_class_entity, benefit_entity):
    return Room.safe_create(
        number='101A',
        adults_capacity=2,
        children_capacity=1,
        size=25,
        short_desc='Nice room',
        long_desc='Very nice room with view',
        room_class=room_class_entity,
        hotel=hotel_entity,
        benefits=[benefit_entity],
        prices=[],  # No prices initially for testing
        available=False,  # Unavailable to avoid validation error
    ).unwrap()
