"""
This module provides a concrete implementation of the AbsClientRepository port.
"""

import logging
from typing import Any

from django.db.models import Q

from clients.domain.entities import Client as ClientEntity
from clients.domain.ports import AbsClientRepository
from clients.models import Client as DjangoClient
from exc import Result
from utils.support import (
    entity_to_model,
    model_to_entity,
    model_validate,
    update_changed_fields,
)

logger = logging.getLogger('djangoLogger')


class ClientRepository(AbsClientRepository):
    """
    A concrete repository for Client entities that uses Django's ORM for data persistence.
    """

    def __init__(self) -> None:
        self._model = DjangoClient

    def add(self, client: ClientEntity) -> Result[ClientEntity]:
        """
        Creates a new client record in the database from a Client entity.
        """
        model_instance_result = entity_to_model(client, self._model).then(model_validate)
        if model_instance_result.is_err():
            src_error = model_instance_result.unwrap_err()
            return Result.Err(msg=src_error.msg, src_error=src_error.src_error)

        model_instance = model_instance_result.unwrap()
        try:
            model_instance.save()
        except Exception as e:
            return Result.Err(msg='Could not save client', src_error=e)

        return self._to_entity(model_instance)

    def get_by_id(self, client_id: int) -> Result[ClientEntity]:
        """Retrieves a client by their ID and converts the model to a domain entity."""
        try:
            client = self._model.objects.get(id=client_id)
            return self._to_entity(client)
        except self._model.DoesNotExist as e:
            return Result.Err(msg=f'Client with id {client_id} does not exist.', src_error=e)
        except Exception as e:
            return Result.Err(
                msg=f'Could not retrieve client with id {client_id}', src_error=e
            )

    def get_by_username(self, username: str) -> Result[ClientEntity]:
        """Retrieves a client by their username."""
        try:
            client = self._model.objects.get(username=username)
            return self._to_entity(client)
        except self._model.DoesNotExist as e:
            return Result.Err(
                msg=f'Client with username {username} does not exist.', src_error=e
            )
        except Exception as e:
            return Result.Err(
                msg=f'Could not retrieve client with username {username}',
                src_error=e,
            )

    def get_by_email(self, email: str) -> Result[ClientEntity]:
        """Retrieves a client by their email."""
        try:
            client = self._model.objects.get(email=email)
            return self._to_entity(client)
        except self._model.DoesNotExist as e:
            return Result.Err(msg=f'Client with email {email} does not exist.', src_error=e)
        except Exception as e:
            return Result.Err(msg=f'Could not retrieve client with email {email}', src_error=e)

    def update(self, client_id: int, **kwargs: Any) -> Result[None]:
        """Updates an existing client's data in the database."""
        try:
            client_to_update = self._model.objects.get(id=client_id)
            update_changed_fields(client_to_update, kwargs)
            return Result.Ok(None)
        except self._model.DoesNotExist as e:
            return Result.Err(msg=f'Client with id {client_id} does not exist.', src_error=e)
        except Exception as e:
            return Result.Err(msg=f'Could not update client with id {client_id}', src_error=e)

    def delete(self, client_id: int) -> Result[None]:
        """Deletes a client from the database by their ID."""
        try:
            client = self._model.objects.get(id=client_id)
            client.delete()
            return Result.Ok(None)
        except self._model.DoesNotExist:
            return Result.Err(msg=f'Client with id {client_id} does not exist.')
        except Exception as e:
            return Result.Err(msg=f'Could not delete client with id {client_id}', src_error=e)

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

            return Result.Ok(exists)
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result.Err(msg='Could not check for duplicate client', src_error=e)

    @staticmethod
    def _to_entity(client_model: DjangoClient) -> Result[ClientEntity]:
        """Converts a Django Client model instance to a domain Client entity."""
        return model_to_entity(client_model, ClientEntity)
