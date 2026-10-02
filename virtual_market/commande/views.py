from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from users.permisions import IsAdminOrSuperAdmin
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer


class IsOrderOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            user.is_superuser
            or user.role in ("admin", "superadmin")
            or obj.items.filter(product__owner=user).exists()
        )


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            qs = Order.objects.select_related("user").prefetch_related("items__product").order_by("-created_at")
        elif user.role == "seller":
            qs = Order.objects.filter(items__product__owner=user).distinct().order_by("-created_at")
        else:
            qs = Order.objects.filter(user=user).order_by("-created_at")
        params = self.request.query_params
        search = params.get("search")
        status = params.get("status")
        if search:
            qs = qs.filter(
                Q(user__username__icontains=search)
                | Q(user__adresse__icontains=search)
                | Q(items__product__owner__shop_name__icontains=search)
            ).distinct()
        if status and status != "all":
            qs = qs.filter(status=status)
        return qs

    def get_permissions(self):
        if self.action == "set_status":
            permission_classes = [IsOrderOwnerOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="shop-orders")
    def shop_orders(self, request):
        """Commandes contenant les produits du commerçant connecté."""
        qs = self.get_queryset().filter(items__product__owner=request.user).distinct()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

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