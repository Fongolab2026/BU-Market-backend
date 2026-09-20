from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    read = serializers.BooleanField(source="is_read", read_only=True)
    time = serializers.DateTimeField(source="created_at", read_only=True)
    kind = serializers.CharField(source="type", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "user_username",
            "title",
            "message",
            "type",
            "kind",
            "is_read",
            "read",
            "time",
            "created_at",
        ]