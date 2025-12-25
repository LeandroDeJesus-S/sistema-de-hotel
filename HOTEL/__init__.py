# Lazy container initialization to avoid Django setup issues
_app_container = None


def get_container():
    """Get the application container, initializing it if necessary."""
    global _app_container
    if _app_container is None:
        from .container import Container

        _app_container = Container()
    return _app_container
