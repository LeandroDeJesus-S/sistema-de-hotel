from typing import Protocol

from django.db import models

from utils import support


class BeforeMiddleware(Protocol):
    def before_save(self, instance: models.Model, is_create: bool): ...


class AfterMiddleware(Protocol):
    def after_save(self, instance: models.Model, is_create: bool): ...


class Middleware(BeforeMiddleware, AfterMiddleware): ...


def model_middleware(*middlewares: Middleware | BeforeMiddleware | AfterMiddleware):
    """model middleware executes operations before and after model's save method"""

    def decorator(model_cls):
        original_save = model_cls.save

        def save(self, *args, **kwargs):
            if kwargs.get('raw'):
                return original_save(self, *args, **kwargs)

            is_create = self._state.adding

            for mw in middlewares:
                hasattr(mw, 'before_save') and mw.before_save(self, is_create=is_create)

            result = original_save(self, *args, **kwargs)

            for mw in reversed(middlewares):
                hasattr(mw, 'after_save') and mw.after_save(self, is_create=is_create)

            return result

        model_cls.save = save
        return model_cls

    return decorator


class ResizeImageMiddleware(BeforeMiddleware):
    """a BeforeMiddleware that resizes an image field"""

    def __init__(
        self, field_name: str, w: int | float, h: int | float | None = None, create_only=True
    ):
        self.field_name = field_name
        self.w = w
        self.h = h
        self.create_only = create_only

    def before_save(self, instance, is_create=False):
        if not is_create and self.create_only:
            return

        img = getattr(instance, self.field_name, None)
        if not img:
            return

        support.resize_image(img.path, self.w, self.h)
