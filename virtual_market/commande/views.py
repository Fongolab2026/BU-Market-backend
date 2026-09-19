from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            return Order.objects.all()
        return Order.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            return OrderItem.objects.all()
        return OrderItem.objects.filter(order__user=user)

    def perform_create(self, serializer):
        order = serializer.validated_data.get("order")
        if order is not None and order.user != self.request.user:
            raise PermissionDenied("Cette commande ne vous appartient pas.")
        serializer.save()