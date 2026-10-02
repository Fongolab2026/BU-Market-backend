from rest_framework import viewsets
from rest_framework.permissions import AllowAny, BasePermission
from .models import Category
from .serializers import CategorySerializer
class IsCategoryManager(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in ("admin", "superadmin", "seller")
            )
        )


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            permission_classes = [IsCategoryManager]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]