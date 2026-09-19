from django.apps import AppConfig


class MessagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messages'
    # 'messages' is already taken by django.contrib.messages, so a unique
    # label is required or Django refuses to start.
    label = 'messaging'
