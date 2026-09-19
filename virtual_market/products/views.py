from django.shortcuts import render
from .models import Product
from rest_framework import viewsets
from .serializers import ProductSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from users.permisions import IsAdmin,IsBuyer,IsSeller,IsSuperAdmin

# Create your views here.
class ProductPagination(PageNumberPagination):
    page_size = 20

class ProductsView(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    # ordering = "name"

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user
        )
        return serializer

    def get_permissions(self):
        if self.action == 'destroy':
            permission_classes = [IsSeller, IsAdmin, IsSuperAdmin]

        elif self.action == 'update':
            permission_classes = [IsSeller, IsAdmin, IsSuperAdmin]

        else:
            permission_classes = [
                IsAuthenticated
            ]
        return [
            permission()
            for permission in permission_classes    

        ]


