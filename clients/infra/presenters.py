from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from clients.feedback_messages import ChangePassword
from exc import Result


def signup_post_presenter(
    request: HttpRequest,
    result: Result[str],
    template_name: str,
    context: dict,
) -> HttpResponse:
    """Presenter for signup post requests.

    Args:
        request: The HTTP request
        result: Result containing redirect URL on success, error message on failure
        template_name: Template to render on error
        context: Context to pass to template

    Returns:
        HttpResponse with redirect or rendered template
    """
    if result.is_err():
        messages.error(request, result.unwrap_err().msg)
        return render(request, template_name, context)

    redirect_url = result.unwrap()
    return redirect(redirect_url)


def signin_post_presenter(
    request: HttpRequest,
    result: Result[str],
    template_name: str,
    context: dict,
) -> HttpResponse:
    """Presenter for signin post requests.

    Args:
        request: The HTTP request
        result: Result containing redirect URL on success, error message on failure
        template_name: Template to render on error
        context: Context to pass to template

    Returns:
        HttpResponse with redirect or rendered template
    """
    if result.is_err():
        messages.error(request, result.unwrap_err().msg)
        return render(request, template_name, context)

    redirect_url = result.unwrap()
    return redirect(redirect_url)


def password_change_post_presenter(
    request: HttpRequest,
    result: Result[None],
    redirect_url: str,
) -> HttpResponse:
    """Presenter for password change post requests.

    Args:
        request: The HTTP request
        result: Result with None on success, error message on failure
        redirect_url: URL to redirect to in both success and error cases

    Returns:
        HttpResponse with redirect
    """
    if result.is_err():
        messages.error(request, result.unwrap_err().msg)
    else:
        messages.success(request, ChangePassword.SUCCESS)

    return redirect(redirect_url)
