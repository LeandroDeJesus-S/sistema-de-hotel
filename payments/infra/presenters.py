from http import HTTPStatus
from typing import Union

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from base.dtos import RedirectResultDTO, TemplateRenderResultDTO
from exc import Result
from payments.domain.dtos import CheckoutResultDTO
from payments.error_messages import CheckoutMessages


def checkout_get_presenter(
    request: HttpRequest,
    o: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]],
) -> Result[HttpResponse]:
    """Returns a Result containing a TemplateRenderResultDTO or RedirectResultDTO
    depending on the result of the reservation use case."""
    if o.is_err():
        messages.error(request, 'Failed to render checkout page')
        return Result.Ok(redirect('rooms'))

    res = o.unwrap()
    if isinstance(res, RedirectResultDTO):
        return Result.Ok(
            redirect(res.url, permanent=res.code == HTTPStatus.PERMANENT_REDIRECT)
        )
    return Result.Ok(render(request, res.template_name, res.context))


def checkout_post_presenter(
    request: HttpRequest, o: Result[CheckoutResultDTO]
) -> Result[HttpResponse]:
    """Returns a Result containing a TemplateRenderResultDTO or RedirectResultDTO
    depending on the result of the reservation use case."""

    def _on_err(_):
        messages.error(request, CheckoutMessages.PAYMENT_FAIL)
        return redirect(request.META.get('HTTP_REFERER', reverse('rooms')))

    def _on_ok(result):
        return redirect(result.session_url)

    return Result.Ok(
        o.match(
            on_err=_on_err,
            on_ok=_on_ok,
        )
    )


def payment_success_get_presenter(
    request: HttpRequest, o: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]]
):
    if o.is_err():
        messages.error(request, CheckoutMessages.PAYMENT_FAIL)
        return redirect(reverse('rooms'))

    res = o.unwrap()
    if isinstance(res, RedirectResultDTO):
        return redirect(res.url, permanent=res.code == HTTPStatus.PERMANENT_REDIRECT)
    return render(request, res.template_name, res.context)


def payment_cancel_get_presenter(
    request: HttpRequest, o: Union[Result[TemplateRenderResultDTO], Result[RedirectResultDTO]]
):
    if o.is_err():
        messages.error(request, 'Failed to render cancel page')
        return redirect(reverse('rooms'))

    res = o.unwrap()
    if isinstance(res, RedirectResultDTO):
        return redirect(res.url, permanent=res.code == HTTPStatus.PERMANENT_REDIRECT)
    return render(request, res.template_name, res.context)
