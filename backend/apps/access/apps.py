from django.apps import AppConfig


class AccessConfig(AppConfig):
    name = "apps.access"

    def ready(self):
        from . import signals  # noqa: F401
