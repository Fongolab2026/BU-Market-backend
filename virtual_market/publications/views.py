from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from products.models import Product
from users.permisions import IsAdminOrSuperAdmin
from .models import PublicationRequest
from .serializers import PublicationRequestSerializer


class PublicationRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationRequestSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("approve", "reject", "update", "partial_update", "destroy", "list", "retrieve"):
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        qs = (
            PublicationRequest.objects.select_related("product__category", "seller")
            .order_by("-created_at")
        )
        if self.request.user.role in ("admin", "superadmin") or self.request.user.is_superuser:
            return qs
        return qs.filter(seller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def _set_status(self, request, pending_status):
        req = self.get_object()
        req.status = pending_status
        req.save()
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["patch"], url_path="approve")
    def approve(self, request, pk=None):
        response = self._set_status(request, PublicationRequest.Status.APPROVED)
        product = self.get_object().product
        product.status = Product.Status.ACTIVE
        product.save(update_fields=["status"])
        return response

    @action(detail=True, methods=["patch"], url_path="reject")
    def reject(self, request, pk=None):
        response = self._set_status(request, PublicationRequest.Status.REJECTED)
        product = self.get_object().product
        product.status = Product.Status.INACTIVE
        product.save(update_fields=["status"])
        return response