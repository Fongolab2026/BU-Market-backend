from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admin.pagination import AdminPageNumberPagination
from notification.models import Notification
from users.models import User
from .models import Message
from .serialzer import MessagesSerializer


class MessagePagination(AdminPageNumberPagination):
    page_size = 20


class MessagesView(viewsets.ModelViewSet):
    """
    Messaging API.

    list      GET    /messages/messages/                 -> messages sent or received by me
    create    POST   /messages/messages/                 -> send a message (sender = me)
    retrieve  GET    /messages/messages/{id}/            -> one of my messages
    update    PATCH  /messages/messages/{id}/            -> edit a message I sent (flagged is_edited)
    destroy   DELETE /messages/messages/{id}/            -> delete a message I sent
    inbox     GET    /messages/messages/inbox/           -> messages I received
    sent      GET    /messages/messages/sent/            -> messages I sent
    conversation GET /messages/messages/conversation/{user_id}/ -> thread with one user
    """
    serializer_class = MessagesSerializer
    pagination_class = MessagePagination
    permission_classes = [IsAuthenticated]
    # PUT is allowed too, but PATCH is the natural verb for a small correction.
    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            # Also keeps drf-spectacular's schema introspection happy.
            return Message.objects.none()
        return (
            Message.objects
            .filter(Q(sender=user) | Q(receiver=user))
            .select_related('sender', 'receiver')
            .order_by('-timestamp')
        )

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        self._notify_receiver(message)

    @staticmethod
    def _notify_receiver(message):
        """Notify the recipient when a new message arrives in their inbox."""
        Notification.objects.create(
            user=message.receiver,
            title=f"Nouveau message de {message.sender.username}",
            message=message.content[:280],
            type=Notification.Type.MESSAGE,
        )

    def perform_update(self, serializer):
        # Only the author can rewrite a message; the receiver keeps the original
        # text he was notified about, plus an "edited" marker.
        if serializer.instance.sender != self.request.user:
            raise PermissionDenied("You can only edit messages you sent.")
        serializer.save(is_edited=True, edited_at=timezone.now())

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {"detail": "You can only delete messages you sent."},
                status=status.HTTP_403_FORBIDDEN,
            )
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def inbox(self, request):
        queryset = self.get_queryset().filter(receiver=request.user)
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'])
    def sent(self, request):
        queryset = self.get_queryset().filter(sender=request.user)
        return self._paginated_response(queryset)

    @action(detail=False, methods=['get'], url_path=r'conversation/(?P<user_id>\d+)')
    def conversation(self, request, user_id=None):
        other = get_object_or_404(User, pk=user_id)
        queryset = (
            self.get_queryset()
            .filter(Q(sender=other) | Q(receiver=other))
            .order_by('timestamp')  # chronological for a chat thread
        )
        return self._paginated_response(queryset)

    def _paginated_response(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='conversations')
    def conversations(self, request):
        """Conversations admin↔interlocuteur : {id, sender, shop, avatar, message, time, unread, status}."""
        user = request.user
        partners = (
            User.objects.filter(
                Q(sent_messages__receiver=user) | Q(received_messages__sender=user)
            ).distinct()
        )
        result = []
        for partner in partners:
            thread = (
                Message.objects.filter(
                    Q(sender=user, receiver=partner) | Q(sender=partner, receiver=user)
                ).order_by('-timestamp')
            )
            last = thread.first()
            unread = thread.filter(receiver=user, is_read=False).count()
            result.append({
                "id": partner.id,
                "sender": partner.username,
                "shop": partner.shop_display_name,
                "avatar": partner.profile_pic.url if partner.profile_pic else None,
                "message": last.content if last else "",
                "time": last.timestamp.isoformat() if last else None,
                "unread": unread,
                "status": "open" if unread else "closed",
            })
        return Response(result)

    @action(detail=True, methods=['patch'], url_path='read')
    def mark_conversation_read(self, request, pk=None):
        partner = get_object_or_404(User, pk=pk)
        Message.objects.filter(sender=partner, receiver=request.user, is_read=False).update(
            is_read=True
        )
        return Response({"detail": "Conversation marquée comme lue."})

    @action(detail=False, methods=['patch'], url_path='read-all')
    def read_all(self, request):
        Message.objects.filter(receiver=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "Tous les messages sont marqués comme lus."})

    @action(detail=False, methods=['post'], url_path='send')
    def send(self, request):
        serializer = self.get_serializer(
            data={
                "receiver": request.data.get("recipient_id"),
                "content": request.data.get("content"),
            }
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user)
        self._notify_receiver(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='contact')
    def contact(self, request):
        """Message du formulaire « Nous contacter » à destination des superadmins.

        Le client connecté écrit au support : le message est livré dans la
        messagerie de chaque superadmin (et une notification y est ajoutée).
        """
        subject = (request.data.get("subject") or "").strip()
        content = (request.data.get("message") or "").strip()
        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()

        if not content:
            return Response(
                {"detail": "Le message est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipients = list(
            User.objects.filter(
                role=User.Role.SUPER_ADMIN, is_active=True
            ).exclude(pk=request.user.pk)
        )
        if not recipients:
            recipients = list(
                User.objects.filter(is_superuser=True, is_active=True)
                .exclude(pk=request.user.pk)
            )
        if not recipients:
            return Response(
                {"detail": "Aucun administrateur disponible pour recevoir le message."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        header = [f"Objet : {subject}"] if subject else []
        if name:
            header.append(f"Nom : {name}")
        if email:
            header.append(f"E-mail : {email}")
        body = "\n".join(header + ["", content]) if header else content

        created = []
        for recipient in recipients:
            message = Message.objects.create(
                sender=request.user, receiver=recipient, content=body
            )
            Notification.objects.create(
                user=recipient,
                title=f"Nouveau message de contact — {subject or request.user.username}",
                message=content[:280],
                type=Notification.Type.MESSAGE,
            )
            created.append(message)

        return Response(
            MessagesSerializer(created[0]).data, status=status.HTTP_201_CREATED
        )
