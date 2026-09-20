from django.shortcuts import render
from .models import Product
from rest_framework import viewsets
from .serializers import ProductSerializer
from admin.pagination import AdminPageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from users.permisions import IsProductOwnerOrAdmin

# Create your views here.
class ProductPagination(AdminPageNumberPagination):
    page_size = 20

class ProductsView(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    ordering = "name"

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user
        )
        return serializer

    def get_permissions(self):
        if self.action in ('destroy', 'update', 'partial_update'):
            permission_classes = [IsProductOwnerOrAdmin]

        elif self.action == 'create':
            permission_classes = [IsAuthenticated]

        else:
            permission_classes = [
                AllowAny
            ]
        return [
            permission()
            for permission in permission_classes    

        ]


