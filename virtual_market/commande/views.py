from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from users.permisions import IsAdminOrSuperAdmin
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer, ShopOrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            return Order.objects.all().order_by("-created_at")
        return Order.objects.filter(user=user).order_by("-created_at")

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            # list / retrieve / create / set_status / shop-orders
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        user = request.user
        is_admin = user.is_superuser or user.role in ("admin", "superadmin")
        
        # L'acheteur peut annuler sa propre commande si elle est encore pending
        if not is_admin:
            order = Order.objects.filter(pk=pk, user=user).first()
            if order:
                # L'acheteur ne peut qu'annuler une commande en attente
                status_name = request.data.get("status")
                if status_name == Order.Status.CANCELLED and order.status == Order.Status.PENDING:
                    order.status = Order.Status.CANCELLED
                    order.save()
                    return Response(OrderSerializer(order).data)
                else:
                    raise PermissionDenied(
                        "Vous ne pouvez annuler que les commandes en attente."
                    )
        
        if is_admin:
            order = get_object_or_404(Order, pk=pk)
        else:
            # Un vendeur ne peut agir que sur une commande contenant ses produits.
            order = (
                Order.objects.filter(pk=pk, items__product__owner=user)
                .distinct()
                .first()
            )
            if order is None:
                raise PermissionDenied(
                    "Vous ne pouvez pas modifier cette commande."
                )
        status_name = request.data.get("status")
        if status_name and status_name not in Order.Status.values:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": "Statut de commande invalide."})
        order.status = status_name or order.status
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=False, methods=["get"], url_path="shop-orders")
    def shop_orders(self, request):
        """Commandes contenant au moins un produit du vendeur connecté.
        Ne renvoie que les articles du vendeur et le total correspondant.
        """
        user = request.user
        # Récupérer les OrderItems du vendeur
        seller_items = OrderItem.objects.filter(
            product__owner=user
        ).select_related("order", "order__user", "product").order_by("-order__created_at")

        # Grouper par commande
        from collections import defaultdict
        orders_dict = defaultdict(lambda: {"order": None, "items": [], "total": 0})
        for item in seller_items:
            order_id = item.order_id
            if orders_dict[order_id]["order"] is None:
                orders_dict[order_id]["order"] = item.order
            orders_dict[order_id]["items"].append(item)
            orders_dict[order_id]["total"] += item.subtotal

        # Appliquer les filtres
        search = request.query_params.get("search")
        status_param = request.query_params.get("status")
        
        filtered_orders = []
        for order_data in orders_dict.values():
            order = order_data["order"]
            if search:
                filters = (
                    Q(user__username__icontains=search)
                    | Q(user__first_name__icontains=search)
                    | Q(user__last_name__icontains=search)
                )
                if str(search).isdigit():
                    filters |= Q(id=int(search))
                if not order.user.username.__contains__(search) and not order.user.first_name.__contains__(search) and not order.user.last_name.__contains__(search) and (not str(search).isdigit() or order.id != int(search)):
                    continue
            if status_param and status_param != "all" and order.status != status_param:
                continue
            filtered_orders.append(order_data)

        # Trier par date
        filtered_orders.sort(key=lambda x: x["order"].created_at, reverse=True)

        # Pagination
        page = self.paginate_queryset(filtered_orders)
        if page is not None:
            serializer = ShopOrderSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = ShopOrderSerializer(filtered_orders, many=True, context={"request": request})
        return Response(serializer.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            return OrderItem.objects.all().order_by("-id")
        return OrderItem.objects.filter(order__user=user).order_by("-id")

    def get_permissions(self):
        # Seuls les admins peuvent créer/modifier des OrderItems directement
        # Les acheteurs passent par le panier (checkout)
        if self.action in ("create", "update", "partial_update", "destroy"):
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        order = serializer.validated_data.get("order")
        if order is not None and order.user != self.request.user:
            raise PermissionDenied("Cette commande ne vous appartient pas.")
        serializer.save()