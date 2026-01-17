from functools import wraps
from typing import Type, TypeVar

import requests
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from django.shortcuts import redirect
from django.utils.translation import gettext as gt
from django.utils.translation import gettext_lazy as gtl
from PIL import Image

from base.entity import BaseEntity
from clients.feedback_messages import Recaptcha
from exc import Result
from reservations.domain.entities import Reservation as ReservationEntity
from reservations.rules import ReserveRules


def resize_image(img_path, w, h=None):
    """Resizes an image to specified dimensions.

    Args:
        img_path (Any): Path to the image.
        w (int): Width of the image.
        h (int, optional): Height of the image. Defaults to None.
    """
    img = Image.open(img_path)
    original_w, original_h = img.size

    if h is None:
        h = round(w * original_h / original_w)
    h = min(original_h, h)

    resized = img.resize((w, h), Image.Resampling.NEAREST)
    resized.save(img_path, optimize=True, quality=70)

    resized.close()
    img.close()


def verify_captcha(captcha_resp) -> bool:
    """Performs Google reCAPTCHA v3 validation.

    Args:
        captcha_resp (Any): User's captcha response.

    Returns:
        bool: Returns True if the captcha is valid.
    """
    MIN_SCORE = settings.CAPTCHA_MIN_SCORE
    data = {
        'response': captcha_resp,
        'secret': settings.G_RECAPTCHA_KEY_SECRET,
    }
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify', data=data, timeout=5
        )
    except requests.Timeout:
        return False

    json_resp = response.json()
    success = json_resp.get('success', False)
    score = json_resp.get('score', 0)
    good_score = score >= MIN_SCORE
    is_valid = success and good_score
    return True if is_valid else False


def captcha_required(
    on_fail_redirect: str, on_fail_message: str = Recaptcha.INVALID_MESSAGE, params=None
):
    """
    Decorator that checks if the request contains a valid recaptcha response.

    If the captcha is invalid, it redirects the user to the on_fail_redirect url.

    Args:
        on_fail_redirect (str): url to redirect the user if the captcha is invalid
        on_fail_message (str, optional): message to display if the captcha is invalid.
            Defaults to INVALID_RECAPTCHA_MESSAGE.
    """

    if not isinstance(params, tuple) and params is not None:
        raise TypeError('params must be a tuple')
    elif params is None:
        params = ()

    def decorator(func):
        @wraps(func)
        def decorated(request, *args, **kwargs):
            captcha_resp = request.POST.get('g-recaptcha-response')

            if not verify_captcha(captcha_resp):
                messages.error(request, on_fail_message)
                return redirect(on_fail_redirect, **{k: kwargs[k] for k in params})

            return func(request, *args, **kwargs)

        return decorated

    return decorator


def update_changed_fields(model_instance, update_data: dict) -> list[str]:
    """
    Updates only the fields of a model instance that have actually changed.

    Args:
        model_instance: The Django model instance to update.
        update_data: A dictionary containing the new data to compare against.

    Returns:
        A list of the field names that were updated.
    """
    updated_fields = []
    for field, value in update_data.items():
        if (
            value
            and hasattr(model_instance, field)
            and getattr(model_instance, field) != value
        ):
            setattr(model_instance, field, value)
            updated_fields.append(field)

    if updated_fields:
        model_instance.full_clean()
        model_instance.save(update_fields=updated_fields)

    return updated_fields


T = TypeVar('T', bound=BaseEntity)
M = TypeVar('M', bound=models.Model)


def model_to_entity(model: M, entity_cls: Type[T]) -> Result[T]:
    def to_dict(instance):
        if not instance:
            return None

        opts = instance._meta
        data = {}
        for f in opts.concrete_fields + opts.many_to_many:
            value = getattr(instance, f.name)
            if isinstance(f, models.ManyToManyField):
                data[f.name] = [to_dict(related) for related in value.all()]
            elif isinstance(f, models.ForeignKey):
                data[f.name] = to_dict(value)
            elif isinstance(value, ImageFieldFile):
                data[f.name] = value.name if value else ''
            elif value is None and f.get_internal_type() in {'CharField', 'TextField'}:
                data[f.name] = ''
            else:
                data[f.name] = value
        return data

    model_dict = to_dict(model)
    entity = entity_cls.safe_validate(model_dict)
    if entity.is_err():
        return Result.Err(
            msg='Failed to convert model to entity', src_error=entity.unwrap_err()
        )
    return Result.Ok(entity.unwrap())


def models_to_entities(models_queryset, entity_cls: Type[T]) -> Result[list[T]]:
    entities: list[T] = []
    for instance in models_queryset:
        entity_result = model_to_entity(instance, entity_cls)
        if entity_result.is_err():
            return Result.Err(
                msg='Failed to convert models to entities',
                src_error=entity_result.unwrap_err(),
            )
        entities.append(entity_result.unwrap())
    return Result.Ok(entities)


def entity_to_model(entity: BaseEntity, model_cls: Type[M]) -> Result[M]:
    """
    Converts a Pydantic entity to a Django model instance, ready for creation or update.
    This function does NOT save the model instance to the database.
    It also does not handle ManyToMany relationships, which must be handled by the caller
    after the instance is saved.
    """

    try:
        model_data = {}
        for field_name, value in entity.model_dump(exclude_none=True).items():
            if isinstance(value, list):
                continue

            if isinstance(value, dict) and 'id' in value and value['id'] is not None:
                model_data[f'{field_name}_id'] = value['id']
            elif field_name not in {'id'}:
                model_data[field_name] = value

        if entity.id:
            # It's an update, get the existing instance
            try:
                instance = model_cls.objects.get(id=entity.id)
                for key, value in model_data.items():
                    setattr(instance, key, value)
            except model_cls.DoesNotExist as e:
                return Result.Err(
                    msg=f'Instance with id {entity.id} not found for update.',
                    src_error=e,
                )
        else:
            # It's a creation
            instance = model_cls(**model_data)

        return Result.Ok(instance)

    except Exception as e:
        return Result.Err(msg=str(e), src_error=e)


def model_validate(model: M) -> Result[M]:
    """calls full_clean on a model instance"""
    try:
        model.full_clean()
        return Result.Ok(model)
    except ValidationError as e:
        return Result.Err(msg=str(e), src_error=e)


def get_available_dates_message(reservations: list[ReservationEntity]) -> Result[str]:
    """Returns a formatted string with the available dates for a room.

    Args:
        reservations (list[ReservationEntity]): A list of reservations **for a same room**.

    Returns:
        str: A formatted string with the available dates for a room.
    """

    datetime_format = '%d %b %Y %H:%M'
    msg_prefix = gt('This room is only available for reservation from')
    msg_parts: list[str] = []
    lst: ReservationEntity | None = None
    for reserva in reservations:
        if lst is None:
            lst = reserva
            continue

        # Calculate the effective end time of previous reservation (including clean time)
        effective_start = reserva.checkin - settings.CLEAN_TIME
        effective_end = lst.checkout + settings.CLEAN_TIME

        # If there's a gap between effective end and next reservation start
        if reserva.checkin > effective_end:
            start, end = (
                effective_end,
                effective_start,
            )
            if (end - start).days > ReserveRules.MIN_RESERVATION_DAYS:
                msg_parts.append(
                    gtl('%(from_datetime)s to %(to_datetime)s')
                    % {
                        'from_datetime': start.strftime(datetime_format),
                        'to_datetime': end.strftime(datetime_format),
                    }
                )

        lst = reserva

    if msg_parts:
        # Add the period after the last reservation
        last_available = reserva.checkout + settings.CLEAN_TIME
        msg_parts.append(
            gtl('and %(datetime)s onwards.')
            % {'datetime': last_available.strftime(datetime_format)}
        )
        joined_msg = ', '.join(msg_parts)
        return Result.Ok(f'{msg_prefix} {joined_msg}')

    # No gaps found, only show after last reservation
    last_available = reserva.checkout + settings.CLEAN_TIME
    msg_parts.append(
        gtl('%(fmt_datetime)s onwards.')
        % {'fmt_datetime': last_available.strftime(datetime_format)}
    )
    joined_msg = ', '.join(msg_parts)
    return Result.Ok(f'{msg_prefix} {joined_msg}')
