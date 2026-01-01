from typing import Generic, Literal, TypeVar

from base.entity import BaseEntity

T = TypeVar('T')


class MessageDTO(BaseEntity):
    typ: Literal['error', 'success', 'info', 'warning']
    msg: str


class TemplateRenderResultDTO(BaseEntity, Generic[T]):  # noqa: F821
    """Data Transfer Object for rendering a template.

    Attributes:
        template_name (str): The name of the template to render.
        context (dict[str, T]): The context data to pass to the template.
        messages (list[MessageDTO]): Optional messages to display.
    """

    template_name: str
    context: dict[str, T]
    messages: list[MessageDTO] = []


class RedirectResultDTO(BaseEntity):
    """Data Transfer Object for redirecting to a URL.

    Attributes:
        url (str): The URL to redirect to.
        args (tuple): The arguments to pass to the URL.
        code (int): The HTTP status code to use for the redirect.
        messages (list[MessageDTO]): Optional messages to display.
    """

    url: str
    args: tuple = ()
    code: int = 302
    messages: list[MessageDTO] = []
