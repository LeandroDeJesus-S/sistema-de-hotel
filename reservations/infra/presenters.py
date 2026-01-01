from http import HTTPStatus
from typing import Any, Union

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from exc import Result


def reserve_get_presenter(
    request: HttpRequest,
    result: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]],
    room_id: int,
) -> Result[HttpResponse]:
    """Presenter for reserve get requests."""
    res = result.unwrap()
    for msg in res.messages:
        getattr(messages, msg.typ)(request, msg.msg)
    if isinstance(res, RedirectResultDTO):
        return Result.Ok(
            redirect(
                reverse(res.url, args=res.args),
                permanent=res.code == HTTPStatus.PERMANENT_REDIRECT,
            )
        )
    res.context['room_pk'] = room_id
    return Result.Ok(render(request, res.template_name, res.context))


def reserve_post_presenter(
    request: HttpRequest,
    result: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]],
) -> Result[HttpResponse]:
    """Presenter for reserve post requests."""
    res = result.unwrap()
    for msg in res.messages:
        getattr(messages, msg.typ)(request, msg.msg)
    if isinstance(res, RedirectResultDTO):
        return Result.Ok(
            redirect(
                reverse(res.url, args=res.args),
                permanent=res.code == HTTPStatus.PERMANENT_REDIRECT,
            )
        )
    return Result.Ok(render(request, res.template_name, res.context))


def cancel_reservation_get_presenter(
    request: HttpRequest,
    result: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]],
) -> Result[HttpResponse]:
    """Presenter for cancel reservation get requests."""
    res = result.unwrap()
    for msg in res.messages:
        getattr(messages, msg.typ)(request, msg.msg)
    if isinstance(res, RedirectResultDTO):
        return Result.Ok(
            redirect(
                reverse(res.url, args=res.args),
                permanent=res.code == HTTPStatus.PERMANENT_REDIRECT,
            )
        )
    return Result.Ok(render(request, res.template_name, res.context))


def cancel_reservation_post_presenter(
    request: HttpRequest,
    result: Result[Any],
) -> Result[RedirectResultDTO]:
    """Presenter for cancel reservation post requests."""

    res = result.unwrap()
    for msg in res.messages:
        getattr(messages, msg.typ)(request, msg.msg)
    if isinstance(res, RedirectResultDTO):
        return Result.Ok(
            redirect(
                reverse(res.url, args=res.args),
                permanent=res.code == HTTPStatus.PERMANENT_REDIRECT,
            )
        )
    return Result.Ok(render(request, res.template_name, res.context))
