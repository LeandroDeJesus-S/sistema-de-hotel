from typing import Generic, TypeVar

from base.entity import BaseEntity

T = TypeVar('T')


class TemplateRenderResultDTO(BaseEntity, Generic[T]):  # noqa: F821
    """Data Transfer Object for rendering a template.

    Attributes:
        template_name (str): The name of the template to render.
        context (dict[str, T]): The context data to pass to the template.
    """

    template_name: str
    context: dict[str, T]


class RedirectResultDTO(BaseEntity):
    """Data Transfer Object for redirecting to a URL.

    Attributes:
        url (str): The URL to redirect to.
        args (tuple): The arguments to pass to the URL.
        code (int): The HTTP status code to use for the redirect.
    """

    url: str
    args: tuple = ()
    code: int = 302
