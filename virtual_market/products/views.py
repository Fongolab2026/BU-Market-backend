from django.db.models import Q
from django.shortcuts import render
from .models import Product, ProductImage
from rest_framework import viewsets
from rest_framework.decorators import action
from .serializers import ProductSerializer, ProductImageSerializer
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
        search = self.request.query_params.get("search")
        status = self.request.query_params.get("status")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(details__icontains=search))
        if status:
            qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        return serializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views += 1
        instance.save(update_fields=["views"])
        return super().retrieve(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == "set_status":
            permission_classes = [IsAdminOrSuperAdmin]
        elif self.action == "upload_images":
            permission_classes = [IsAuthenticated]
        elif self.action in ('destroy', 'update', 'partial_update'):
            permission_classes = [IsProductOwnerOrAdmin]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

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