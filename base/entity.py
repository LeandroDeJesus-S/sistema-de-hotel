import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import PrivateAttr, ValidationError

from exc import Error, Result

T = TypeVar('T', bound='BaseEntity')
logger = logging.getLogger('djangoLogger')


class BaseEntity(PydanticBaseModel):
    """
    A custom Pydantic BaseModel that provides a safe validation method
    which returns a Result object instead of raising a ValidationError.
    """

    _messages: dict[str, dict[str, str]] = {}

    @classmethod
    def safe_validate(cls: Type[T], data: Any) -> Result[T | None]:
        """
        Safely validates data and creates an instance of the model.

        Instead of raising a ValidationError, this method returns a Result
        object containing either the validated model instance or an Error.

        It works in failfasting mode, so it will stop at the first error.

        Args:
            data: The data to validate, can be a dict or another object.

        Returns:
            A Result tuple with the model instance or an Error.
        """
        try:
            logger.debug(f'validating {data}')
            instance = cls.model_validate(data, from_attributes=True)
            logger.debug(f'validated {instance}')
            return Result(value=instance, error=None)
        except ValidationError as e:
            errors = e.errors()
            custom_messages = getattr(cls, '_messages', PrivateAttr(default={}))
            if hasattr(custom_messages, 'get_default'):
                custom_messages = custom_messages.get_default()

            logger.debug(f'custom messages: {custom_messages}')

            for error in errors:
                error_type = error['type']
                if error['loc']:
                    field_name, *_ = error['loc']
                    default_error_msg = f'{field_name}: {error["msg"]}'
                    field_messages = custom_messages.get(field_name, {})
                    current_field_message = field_messages.get(error_type, default_error_msg)
                else:
                    field_name = '__root__'
                    default_error_msg = error['msg']
                    field_messages = custom_messages.get(field_name, {})
                    current_field_message = field_messages.get(error_type, default_error_msg)

                return Result(value=None, error=Error(msg=current_field_message, src_error=e))

            return Result(value=None, error=Error(msg='Validation error', src_error=e))

    @classmethod
    def safe_create(cls: Type[T], **kwargs: Any) -> Result[T | None]:
        """
        Safely creates an instance of the model from keyword arguments.

        This is a convenience method that wraps `safe_validate`.

        Returns:
            A Result tuple with the model instance or an Error.
        """
        return cls.safe_validate(kwargs)
