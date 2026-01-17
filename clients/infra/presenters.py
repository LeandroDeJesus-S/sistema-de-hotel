from http import HTTPStatus
from typing import Union

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from exc import Result


def signup_post_presenter(
    request: HttpRequest,
    result: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]],
) -> Result[HttpResponse]:
    """Presenter for signup post requests.

    Args:
        request: The HTTP request
        result: Result containing DTO

    Returns:
        Result containing HttpResponse with redirect or rendered template
    """
    res = result.unwrap()
    for msg in res.messages:
        getattr(messages, msg.typ)(request, msg.msg)
    if isinstance(res, TemplateRenderResultDTO):
        return Result.Ok(render(request, res.template_name, res.context))
    return Result.Ok(
        redirect(
            reverse(res.url, args=res.args),
            permanent=res.code == HTTPStatus.PERMANENT_REDIRECT,
        )
    )


def signin_post_presenter(
    request: HttpRequest,
    result: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]],
) -> Result[HttpResponse]:
    """Presenter for signin post requests.

    Args:
        request: The HTTP request
        result: Result containing DTO

    Returns:
        Result containing HttpResponse with redirect or rendered template
    """
    res = result.unwrap()
    for msg in res.messages:
        getattr(messages, msg.typ)(request, msg.msg)
    if isinstance(res, TemplateRenderResultDTO):
        return Result.Ok(render(request, res.template_name, res.context))
    return Result.Ok(
        redirect(
            reverse(res.url, args=res.args) if '/' not in res.url else res.url,
            permanent=res.code == HTTPStatus.PERMANENT_REDIRECT,
        )
    )


def password_change_post_presenter(
    request: HttpRequest,
    result: Result[RedirectResultDTO],
) -> Result[HttpResponse]:
    """Presenter for password change post requests.

    Args:
        request: The HTTP request
        result: Result with RedirectResultDTO

    Returns:
        Result containing HttpResponse with redirect
    """
    res = result.unwrap()
    for msg in res.messages:
        getattr(messages, msg.typ)(request, msg.msg)

    return Result.Ok(
        redirect(
            reverse(res.url, args=res.args),
            permanent=res.code == HTTPStatus.PERMANENT_REDIRECT,
        )
    )
