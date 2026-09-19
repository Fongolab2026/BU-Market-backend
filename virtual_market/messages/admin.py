from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('sender__username', 'receiver__username', 'content')
    ordering = ('-timestamp',)
