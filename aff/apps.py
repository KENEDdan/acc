from django.apps import AppConfig


class AffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aff'

    def ready(self):
        import aff.signals  # noqa