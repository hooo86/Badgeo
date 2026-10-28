from django.apps import AppConfig


class Config(AppConfig):
    name = "apps.licensing"

    def ready(self):
        from . import quotas  # noqa: F401  (registers pre_save receivers)
