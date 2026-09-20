from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from users.permisions import IsAdminOrSuperAdmin
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            return Order.objects.all().order_by("-created_at")
        return Order.objects.filter(user=user).order_by("-created_at")

    def get_permissions(self):
        if self.action == "set_status":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        order = self.get_object()
        status_name = request.data.get("status")
        if status_name and status_name not in Order.Status.values:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": "Statut de commande invalide."})
        order.status = status_name or order.status
        order.save()
        return Response(OrderSerializer(order).data)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            return OrderItem.objects.all().order_by("-id")
        return OrderItem.objects.filter(order__user=user).order_by("-id")

    def perform_create(self, serializer):
        order = serializer.validated_data.get("order")
        if order is not None and order.user != self.request.user:
            raise PermissionDenied("Cette commande ne vous appartient pas.")
        serializer.save()