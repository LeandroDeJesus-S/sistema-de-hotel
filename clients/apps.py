from django.apps import AppConfig


class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clients'

    def ready(self) -> None:
        from clients.container import ClientsContainer  # noqa: PLC0415
        from HOTEL import settings  # noqa: PLC0415

        clients_container = ClientsContainer()
        clients_container.config.from_dict(settings.__dict__)
        clients_container.wire(modules=['.views'])
