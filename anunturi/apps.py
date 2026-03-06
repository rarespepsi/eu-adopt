from django.apps import AppConfig


class AnunturiConfig(AppConfig):
    name = 'anunturi'

    def ready(self):
        import anunturi.signals  # noqa: F401
