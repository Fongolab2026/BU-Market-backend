from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from notification.models import Notification
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from products.models import Product
from products.serializers import ProductSerializer
from users.models import User
from users.permisions import IsAdminOrSuperAdmin
from .models import Boutique
from .serializers import BoutiqueSerializer, ShopSerializer


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

class BoutiqueViewSet(viewsets.ModelViewSet):
    """Demandes de location d'espace issues de la page /louer-espace."""

    serializer_class = BoutiqueSerializer
    queryset = Boutique.objects.all()

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminOrSuperAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")
        if search:
            qs = qs.filter(
                Q(company_name__icontains=search)
                | Q(owner_name__icontains=search)
                | Q(province__icontains=search)
            )
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        if user is not None:
            # Un commerçant ne peut avoir qu'une seule boutique.
            if hasattr(user, "boutique") or user.role == User.Role.SELLER:
                raise ValidationError(
                    "Vous possédez déjà une boutique. Une seule boutique est autorisée par compte."
                )
        boutique = serializer.save(owner=user)
        self._notify_admins(boutique)

    def _notify_admins(self, boutique):
        """Crée une notification pour chaque administrateur."""
        admins = get_user_model().objects.filter(
            models.Q(role=User.Role.ADMIN) | models.Q(role=User.Role.SUPER_ADMIN)
        )
        for admin in admins:
            Notification.objects.create(
                user=admin,
                type=Notification.Type.SHOP,
                title="Nouvelle demande de location d'espace",
                message=(
                    f"{boutique.company_name} ({boutique.province}) a envoyé une demande. "
                    "Validez ou rejetez la demande depuis le tableau de bord."
                ),
            )

    def _set_status(self, request, new_status):
        boutique = self.get_object()
        boutique.status = new_status
        boutique.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(boutique).data)

    def _promote_to_seller(self, boutique):
        """L'utilisateur devient commerçant et alimente les champs shop_* historiques."""
        owner = boutique.owner
        if owner is None:
            owner = get_user_model().objects.filter(email__iexact=boutique.email).first()
            if owner is not None:
                boutique.owner = owner
                boutique.save(update_fields=["owner", "updated_at"])
        if owner is None:
            return None
        owner.role = User.Role.SELLER
        owner.shop_name = boutique.company_name
        owner.shop_description = boutique.slogan
        owner.adresse = ", ".join(
            [p for p in (boutique.province, boutique.commune, boutique.neighborhood) if p]
        )
        owner.save(update_fields=["role", "shop_name", "shop_description", "adresse"])
        return owner

    @action(detail=True, methods=["patch"], url_path="validate")
    def validate_shop(self, request, pk=None):
        boutique = self.get_object()
        boutique.status = Boutique.Status.VALIDATED
        boutique.save(update_fields=["status", "updated_at"])
        self._promote_to_seller(boutique)
        boutique.refresh_from_db()
        return Response(self.get_serializer(boutique).data)

    @action(detail=True, methods=["patch"], url_path="reject")
    def reject(self, request, pk=None):
        return self._set_status(request, Boutique.Status.REJECTED)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        return self._set_status(request, request.data.get("status", Boutique.Status.PENDING))

    @action(detail=False, methods=["get"], url_path="pending-count")
    def pending_count(self, request):
        return Response(
            {"count": Boutique.objects.filter(status=Boutique.Status.PENDING).count()}
        )
