from django.db import models

# Create your models here.

class Message(models.Model):
    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # Each edit is flagged so the receiver can see the message was changed
    # after it was sent (same convention as Telegram/WhatsApp).
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} at {self.timestamp}"

# explenation 