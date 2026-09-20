from django.apps import AppConfig


class AdminConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin"
    label = "admin_api"
    verbose_name = "Administration"