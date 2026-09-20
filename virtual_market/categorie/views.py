from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Category
from .serializers import CategorySerializer
from users.permisions import IsAdminOrSuperAdmin


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]