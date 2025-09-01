from pydantic import BaseModel

from .value_objects import CPF, Birthdate, Email, Password, PhoneNumber, Username


class Client(BaseModel):
    """
    Client represents a user client from the hotel.
    """

    username: Username
    first_name: str
    last_name: str
    birthdate: Birthdate
    email: Email
    phone: PhoneNumber
    cpf: CPF
    password: Password
    id: int | None = None
