import io
from datetime import date, datetime
from functools import wraps
from secrets import token_hex
from typing import Type, TypeVar

import requests
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from django.shortcuts import redirect
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from base.entity import BaseEntity
from clients.feedback_messages import Recaptcha
from exc import Result
from home.models import Contact, Hotel
from payments.models import Payment


class PaymentPDFHandler:
    """Cria o pdf com dados do pagamento e envia para o cliente via email."""

    def __init__(self, payment: Payment, hotel_id=1) -> None:
        self.payment = payment
        self._pdf_suffix = token_hex(16)
        self.pdf_name = f'comprovante_de_pagamento_{self.payment.pk}.pdf'
        y = A4[1] * 0.5
        self.pagesize = (A4[0], y)
        self.buffer = io.BytesIO()
        self._canvas = canvas.Canvas(self.buffer, pagesize=self.pagesize)
        self.w, self.h = self.pagesize
        self.hotel = Hotel.objects.get(pk=hotel_id)
        self.hotel_contact = Contact.objects.get(hotel=self.hotel)

    def handle(self):
        """template method that generate the pdf and sent by email to the client"""
        self._draw_header()
        self._draw_body()
        self._save()
        return self._send_email()

    def _rows_list(self):
        """return all the rows of the pdf in list format"""
        rows = [
            f'Data de emissão: {self.payment.created_at.strftime("%h:%M:%S %d/%m/%Y")}',
            f'Status: {self.payment.status}',
            f'Pagador: {self.payment.reservation.client.complete_name}',
            f'Recebedor: HOTEL'
            f'Check-in: {self.payment.reservation.checkin.strftime("%d/%m/%Y")}',
            f'Check-out: {self.payment.reservation.checkout.strftime("%d/%m/%Y")}',
            f'Classe: {self.payment.reservation.room.room_class}',
            f'Quarto: Nº{self.payment.reservation.room.number}',
            f'Total: {self.payment.reservation.formatted_price()}',
        ]
        return rows

    def _draw_header(self):
        """draw the logo, hotel name, and title of the pdf"""
        if self.hotel.logo:
            self._canvas.drawInlineImage(str(self.hotel.logo.path), 30, self.h - 40)

        self._canvas.setFontSize(30)
        self._canvas.drawString(65, self.h - 38, self.hotel.name)

        self._canvas.setFontSize(20)
        self._canvas.drawString(
            self.w - 350,
            self.h - 40,
            'COMPROVANTE DE PAGAMENTO',
            wordSpace=0.5,
        )

        self._canvas.line(30, self.h - 50, self.w - 30, self.h - 50)

    def _draw_body(self):
        """draw the payment information into the body of the pdf"""
        self._canvas.setFontSize(15)
        initial_offset = 85
        offset_y = initial_offset
        for row in self._rows_list():
            self._canvas.drawString(70, self.h - offset_y, row)
            offset_y += initial_offset * 0.5

    def _save(self):
        """save the generated pdf in the buffer"""
        self._canvas.save()
        self.buffer.seek(0)

    def _send_email(self):
        """send the email with the generated pdf to the client and return 1 if
        the email was sent correctly
        """
        msg = EmailMessage(
            subject='Comprovante de pagamento  da reserva',
            body=(
                'Seu comprovante de pagamento para a reserva do '
                f'quarto Nº{self.payment.reservation.room.number}'
            ),
            to=[self.payment.reservation.client.email],
            from_email=self.hotel_contact.email,
        )
        msg.attach(self.pdf_name, self.buffer.getvalue(), 'application/pdf')
        return msg.send(fail_silently=False)


def resize_image(img_path, w, h=None):
    """redimensiona imagem com tamanhos expecificados

    Args:
        img_path (Any): caminho da imagem
        w (int): largura da imagem
        h (int, optional): altura da imagem. Defaults to None.
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
    """realiza a validação do google recaptcha v3

    Args:
        captcha_resp (Any): resposta do usuário para o captcha

    Returns:
        bool: retorna True se o captcha é valido
    """
    MIN_SCORE = 0.8
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
    good_score = json_resp.get('score', 0) > MIN_SCORE
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


def fmt_date(value: date, fmt='%d/%m/%Y') -> str:
    """formata a data no formato especificado.

    Args:
        value (date): data a ser formatada
        fmt (str, optional): padrão para a formatação. Defaults to '%d/%m/%Y'.

    Returns:
        str: data formatada.
    """
    return value.strftime(fmt)


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
            elif isinstance(value, datetime):
                data[f.name] = value.date()
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
            if (
                isinstance(value, list)
                and value
                and isinstance(value[0], dict)
                and 'id' in value[0]
            ):
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
