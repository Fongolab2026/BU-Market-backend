from django.db.models import Q
from django.shortcuts import render
from .models import Product, ProductImage
from rest_framework import viewsets
from rest_framework.decorators import action
from .serializers import ProductSerializer, ProductImageSerializer, AdminProductWriteSerializer
from admin.pagination import AdminPageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from users.permisions import IsProductOwnerOrAdmin, IsAdminOrSuperAdmin
from rest_framework.parsers import MultiPartParser, FormParser

# Create your views here.
class ProductPagination(AdminPageNumberPagination):
    page_size = 30

class ProductsView(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("name")
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    ordering = "name"

    def get_queryset(self):
        qs = super().get_queryset().select_related("owner", "category").prefetch_related("images")
        params = self.request.query_params
        search = params.get("search")
        status = params.get("status")
        category = params.get("category")
        shop = params.get("shop")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(details__icontains=search)
                | Q(owner__shop_name__icontains=search)
            )
        if status and status != "all":
            qs = qs.filter(status=status)
        if category and category != "all":
            qs = qs.filter(category_id=category)
        if shop and shop != "all":
            qs = qs.filter(owner_id=shop)
        return qs

    def get_serializer_class(self):
        user = self.request.user
        is_admin = user.is_authenticated and (
            user.is_superuser or user.role in ("admin", "superadmin")
        )
        if is_admin and self.action in ("create", "update", "partial_update"):
            return AdminProductWriteSerializer
        return ProductSerializer

    def perform_create(self, serializer):
        owner_id = self.request.data.get("shopId")
        if owner_id:
            serializer.save(owner_id=owner_id)
        else:
            serializer.save(owner=self.request.user)
        return serializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views += 1
        instance.save(update_fields=["views"])
        return super().retrieve(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == "set_status":
            permission_classes = [IsProductOwnerOrAdmin]
        elif self.action == "upload_images":
            permission_classes = [IsAuthenticated]
        elif self.action in ('destroy', 'update', 'partial_update'):
            permission_classes = [IsProductOwnerOrAdmin]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ('my_products', 'my_stats'):
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["get"], url_path="my-products")
    def my_products(self, request):
        """Produits du commerçant connecté."""
        qs = self.get_queryset().filter(owner=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="my-stats")
    def my_stats(self, request):
        """Statistiques du commerçant connecté."""
        from django.db.models import Count, Sum
        from commande.models import Order, OrderItem
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from datetime import timedelta

        products_qs = Product.objects.filter(owner=request.user)
        total_products = products_qs.count()
        active_products = products_qs.filter(status=Product.Status.ACTIVE).count()
        total_stock = products_qs.aggregate(total=Sum('stock'))['total'] or 0
        total_views = products_qs.aggregate(total=Sum('views'))['total'] or 0

        # Weekly sales
        week_ago = timezone.now() - timedelta(days=7)
        weekly_sales = OrderItem.objects.filter(
            product__owner=request.user,
            order__created_at__gte=week_ago,
            order__status__in=[Order.Status.COMPLETED, Order.Status.SHIPPED]
        ).aggregate(total=Sum('quantity'))['total'] or 0

        # Recent orders
        recent_orders = OrderItem.objects.filter(
            product__owner=request.user
        ).select_related('order', 'product').order_by('-order__created_at')[:10]

        return Response({
            "total_products": total_products,
            "active_products": active_products,
            "total_stock": total_stock,
            "total_views": total_views,
            "weekly_sales": weekly_sales,
        })

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        product = self.get_object()
        product.status = request.data.get("status", product.status)
        product.save()
        return Response(self.get_serializer(product).data)

    @action(detail=True, methods=["post"], url_path="images", parser_classes=[MultiPartParser, FormParser])
    def upload_images(self, request, pk=None):
        product = self.get_object()
        files = request.FILES.getlist("images")
        is_main_flag = request.data.get("is_main", "true").lower() == "true"
        if not files:
            return Response({"detail": "Aucune image envoyée."}, status=400)

        created = []
        for i, f in enumerate(files):
            img = ProductImage.objects.create(
                product=product,
                image=f,
                is_main=(i == 0 and is_main_flag),
            )
            created.append(img)

        return Response(
            ProductImageSerializer(created, many=True, context={"request": request}).data,
            status=201,
        )

    @action(detail=True, methods=["delete"], url_path="images/(?P<image_id>[\\d]+)")
    def remove_image(self, request, pk=None, image_id=None):
        product = self.get_object()
        img = ProductImage.objects.filter(product=product, id=image_id).first()
        if not img:
            return Response({"detail": "Image introuvable."}, status=404)
        img.image.delete(save=False)
        img.delete()
        return Response(status=204)