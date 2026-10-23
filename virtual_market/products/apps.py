from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = 'products'

    def ready(self):
        # Enregistre les signaux (rupture de stock -> retrait + notification).
        from . import signals  # noqa: F401
