from django.db.models import ProtectedError
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from django.db.models import Q
from admin.pagination import AdminPageNumberPagination
from .models import Category
from .serializers import CategorySerializer


class CanManageCategories(BasePermission):
    """Autorise les admins et les vendeurs à gérer les catégories."""

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and (
            user.is_superuser
            or user.role in ("admin", "superadmin")
            or (user.role == "seller" and user.shop_status == "validated")
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        return user.is_authenticated and (
            user.is_superuser
            or user.role in ("admin", "superadmin")
            or (
                user.role == "seller"
                and user.shop_status == "validated"
                and obj.managed_by_id == user.pk
            )
        )


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    pagination_class = AdminPageNumberPagination

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            permission_classes = [CanManageCategories]
        else:
            # list / retrieve : référentiel public (filtres de la vitrine).
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.role == "seller":
            queryset = queryset.filter(
                Q(managed_by__isnull=True) | Q(managed_by=user)
            )
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            serializer.save(managed_by=None)
        else:
            serializer.save(managed_by=user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": "Cette catégorie est utilisée par des produits et ne peut pas être supprimée."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
