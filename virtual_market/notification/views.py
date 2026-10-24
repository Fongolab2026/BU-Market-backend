from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from users.permisions import IsAdminOrSuperAdmin
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Création/édition réservées aux admins ; la suppression et la lecture
        # sont permises au propriétaire (le queryset le limite à ses données).
        if self.action in ("create", "update", "partial_update"):
            permission_classes = [IsAdminOrSuperAdmin]
        elif self.action == "destroy":
            # Le propriétaire ou un admin peut supprimer
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("superadmin", "admin"):
            qs = Notification.objects.all()
        else:
            qs = Notification.objects.filter(user=user)

        is_read = self.request.query_params.get("is_read")
        if is_read is not None and is_read != "":
            qs = qs.filter(is_read=str(is_read).lower() in ("1", "true", "yes"))
        kind = self.request.query_params.get("type")
        if kind:
            qs = qs.filter(type=kind)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.data.get("user")
        serializer.save(
            user_id=user if user else self.request.user.id
        )

    @action(detail=True, methods=["post", "patch"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)

    def destroy(self, request, *args, **kwargs):
        notification = self.get_object()
        user = request.user
        # Le propriétaire ou un admin peut supprimer
        if notification.user != user and not (user.is_superuser or user.role in ("admin", "superadmin")):
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres notifications.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"detail": "Toutes les notifications sont marquées comme lues."})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"count": count})
