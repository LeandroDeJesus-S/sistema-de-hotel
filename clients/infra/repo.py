"""
This module provides a concrete implementation of the AbsClientRepository port.
"""

import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Q

from clients.domain.entities import Client as ClientEntity
from clients.domain.ports import AbsClientRepository
from clients.models import Client as DjangoClient
from exc import Error, Result

logger = logging.getLogger('djangoLogger')


class ClientRepository(AbsClientRepository):
    """
    A concrete repository for Client entities that uses Django's ORM for data persistence.
    """

    def __init__(self) -> None:
        self._model = DjangoClient

    def add(self, client: ClientEntity) -> Result[ClientEntity | None]:
        """
        Creates a new client record in the database from a Client entity.
        """
        try:
            new_client_model = self._model(
                first_name=client.first_name,
                last_name=client.last_name,
                username=client.username,
                email=client.email,
                phone=client.phone,
                password=client.password,
                birthdate=client.birthdate,
                cpf=client.cpf,
            )
            new_client_model.full_clean()
            new_client_model.save()
            return self._to_entity(new_client_model)

        except ValidationError as e:
            logger.warning(e)
            msg = e.messages[0]
            return Result(value=None, error=Error(msg=msg, src_error=e))

        except Exception as e:
            logger.error(e, exc_info=True)
            return Result(value=None, error=Error(msg='Could not create client', src_error=e))

    def get_by_id(self, client_id: int) -> Result[ClientEntity | None]:
        """Retrieves a client by their ID and converts the model to a domain entity."""
        try:
            client = self._model.objects.get(id=client_id)
            return self._to_entity(client)
        except self._model.DoesNotExist as e:
            return Result(
                value=None,
                error=Error(msg=f'Client with id {client_id} does not exist.', src_error=e),
            )
        except Exception as e:
            return Result(
                value=None,
                error=Error(msg=f'Could not retrieve client with id {client_id}', src_error=e),
            )

    def get_by_username(self, username: str) -> Result[ClientEntity | None]:
        """Retrieves a client by their username."""
        try:
            client = self._model.objects.get(username=username)
            return self._to_entity(client)
        except self._model.DoesNotExist as e:
            return Result(
                value=None,
                error=Error(
                    msg=f'Client with username {username} does not exist.', src_error=e
                ),
            )
        except Exception as e:
            return Result(
                value=None,
                error=Error(
                    msg=f'Could not retrieve client with username {username}',
                    src_error=e,
                ),
            )

    def get_by_email(self, email: str) -> Result[ClientEntity | None]:
        """Retrieves a client by their email."""
        try:
            client = self._model.objects.get(email=email)
            return self._to_entity(client)
        except self._model.DoesNotExist as e:
            return Result(
                value=None,
                error=Error(msg=f'Client with email {email} does not exist.', src_error=e),
            )
        except Exception as e:
            return Result(
                value=None,
                error=Error(msg=f'Could not retrieve client with email {email}', src_error=e),
            )

    def update(self, client_id: int, **kwargs: Any) -> Result[None]:
        """Updates an existing client's data in the database."""
        try:
            client_to_update = self._model.objects.get(id=client_id)

            updated_fields = []
            for field, value in kwargs.items():
                if (
                    value
                    and hasattr(client_to_update, field)
                    and getattr(client_to_update, field) != value
                ):
                    setattr(client_to_update, field, value)
                    updated_fields.append(field)

            if not updated_fields:
                return Result(value=None, error=None)

            client_to_update.full_clean()
            client_to_update.save(update_fields=updated_fields)

            return Result(value=None, error=None)
        except self._model.DoesNotExist as e:
            return Result(
                value=None,
                error=Error(msg=f'Client with id {client_id} does not exist.', src_error=e),
            )
        except Exception as e:
            return Result(
                value=None,
                error=Error(msg=f'Could not update client with id {client_id}', src_error=e),
            )

    def delete(self, client_id: int) -> Result[None]:
        """Deletes a client from the database by their ID."""
        try:
            client = self._model.objects.get(id=client_id)
            client.delete()
            return Result(value=None, error=None)
        except self._model.DoesNotExist:
            return Result(
                value=None, error=Error(msg=f'Client with id {client_id} does not exist.')
            )
        except Exception as e:
            return Result(
                value=None,
                error=Error(msg=f'Could not delete client with id {client_id}', src_error=e),
            )

    def check_duplicate(self, client: ClientEntity) -> Result[bool]:
        """
        Checks for existing clients with the same username, email, phone or cpf.
        """
        try:
            query = (
                Q(username=client.username)
                | Q(email=client.email)
                | Q(phone=client.phone)
                | Q(cpf=client.cpf)
            )
            if client.id:
                exists = self._model.objects.filter(query).exclude(id=client.id).exists()
            else:
                exists = self._model.objects.filter(query).exists()

            return Result(value=exists, error=None)
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result(
                value=False,
                error=Error(msg='Could not check for duplicate client', src_error=e),
            )

    @staticmethod
    def _to_entity(client_model: DjangoClient) -> Result[ClientEntity | None]:
        """Converts a Django Client model instance to a domain Client entity."""
        return ClientEntity.safe_validate(client_model.__dict__)
