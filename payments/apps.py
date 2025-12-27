from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'

    def ready(self) -> None:
        from HOTEL import settings  # noqa: PLC0415

        from .container import PaymentsContainer  # noqa: PLC0415

        payments_container = PaymentsContainer()
        payments_container.config.from_dict(settings.__dict__)
        payments_container.wire(modules=['.views', '.infra.tasks'])
