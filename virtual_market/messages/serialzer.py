from .models import Message
from rest_framework import serializers

class MessagesSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'sender',
            'sender_username',
            'receiver',
            'receiver_username',
            'content',
            'timestamp',
            'is_read',
            'is_edited',
            'edited_at',
        ]
        # The sender is always the authenticated user, never taken from the payload.
        read_only_fields = ['id', 'sender', 'timestamp', 'is_read', 'is_edited', 'edited_at']

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty.")
        return value

    def validate_receiver(self, value):
        request = self.context.get('request')
        if request and request.user == value:
            raise serializers.ValidationError("You cannot send a message to yourself.")
        return value