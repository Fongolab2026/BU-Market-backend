from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from products.models import Product
from products.serializers import ProductSerializer
from users.models import User
from users.permisions import IsAdminOrSuperAdmin
from .serializers import ShopSerializer


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ShopSerializer
    queryset = (
        User.objects.filter(role=User.Role.SELLER)
        .select_related("shop_category")
        .order_by("-date_joined")
    )

    def get_permissions(self):
        if self.action in ("add_product",) and self.request.method == "POST":
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminOrSuperAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        shop_status = self.request.query_params.get("status")
        if search:
            qs = qs.filter(
                Q(username__icontains=search) | Q(shop_name__icontains=search)
            )
        if shop_status:
            qs = qs.filter(shop_status=shop_status)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.shop_views += 1
        instance.save(update_fields=["shop_views"])
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="validate")
    def validate(self, request, pk=None):
        shop = self.get_object()
        shop.shop_status = User.ShopStatus.VALIDATED
        shop.save()
        return Response(self.get_serializer(shop).data)

    @action(detail=True, methods=["patch"], url_path="suspend")
    def suspend(self, request, pk=None):
        shop = self.get_object()
        shop.shop_status = User.ShopStatus.SUSPENDED
        shop.save()
        return Response(self.get_serializer(shop).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        shop = self.get_object()
        shop.shop_status = request.data.get("status", shop.shop_status)
        shop.save()
        return Response(self.get_serializer(shop).data)

    @action(detail=True, methods=["post"], url_path="products")
    def add_product(self, request, pk=None):
        shop = self.get_object()
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=shop)
        return Response(serializer.data, status=status.HTTP_201_CREATED)