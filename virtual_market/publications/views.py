from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from products.models import Product
from users.permisions import IsAdminOrSuperAdmin, IsSellerOrAdmin
from .models import PublicationRequest
from .serializers import PublicationRequestSerializer


class PublicationRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationRequestSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("approve", "reject", "update", "partial_update", "destroy", "list", "retrieve"):
            permission_classes = [IsAdminOrSuperAdmin]
        elif self.action == "create":
            # Seuls les vendeurs (et admins) soumettent un produit a publication.
            permission_classes = [IsSellerOrAdmin]
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
        product = serializer.validated_data["product"]
        user = self.request.user
        is_admin = user.is_superuser or user.role in ("admin", "superadmin")
        if not is_admin and product.owner_id != user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous ne pouvez demander la publication que de vos produits.")
        if PublicationRequest.objects.filter(
            product=product, status=PublicationRequest.Status.PENDING
        ).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"product_id": "Une demande de publication est déjà en cours."})
        serializer.save(seller=user)

    def _set_status(self, request, pending_status):
        req = self.get_object()
        if req.status != PublicationRequest.Status.PENDING:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": "Cette demande a déjà été traitée."})
        req.status = pending_status
        req.save()
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["patch"], url_path="approve")
    def approve(self, request, pk=None):
        req = self.get_object()
        product = req.product
        if not product.images.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"product": "Ajoutez une image avant d'approuver ce produit."})
        if product.stock <= 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"product": "Le stock doit être positif avant publication."})
        response = self._set_status(request, PublicationRequest.Status.APPROVED)
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
