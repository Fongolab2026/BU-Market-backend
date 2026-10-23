from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.permisions import IsAdminOrSuperAdmin
from admin.pagination import AdminPageNumberPagination
from .models import Favorite
from .serializers import FavoriteSerializer, ReviewSerializer


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AdminPageNumberPagination

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("product", "product__owner")
            .prefetch_related("product__images")
        )

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data["product"]
        if Favorite.objects.filter(user=user, product=product).exists():
            raise ValidationError("Ce produit est déjà dans vos favoris.")
        # Par défaut, un favori n'a pas de note (stars=1 par défaut du modèle, mais on ne l'utilise pas comme note)
        # La note sera ajoutée via l'endpoint reviews si l'utilisateur veut noter
        serializer.save(user=user, stars=1, comment="", status=Favorite.Status.VISIBLE)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    queryset = (
        Favorite.objects.select_related("user", "product__owner").order_by("-created_at")
    )
    pagination_class = AdminPageNumberPagination

    def get_permissions(self):
        if self.action in ("create", "list", "retrieve"):
            # Les acheteurs peuvent créer/lire leurs avis
            permission_classes = [IsAuthenticated]
        else:
            # hide/reveal/update/delete réservés aux admins
            permission_classes = [IsAdminOrSuperAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            return self.queryset
        # Les acheteurs ne voient que leurs propres avis
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data["product"]
        # Vérifier que l'utilisateur a acheté ce produit (optionnel, mais recommandé)
        from commande.models import OrderItem
        has_purchased = OrderItem.objects.filter(
            order__user=user,
            product=product,
            order__status__in=["completed", "shipped", "confirmed"]
        ).exists()
        # On permet l'avis même sans achat pour l'instant, mais on pourrait l'exiger
        if Favorite.objects.filter(user=user, product=product).exists():
            raise ValidationError("Vous avez déjà laissé un avis pour ce produit.")
        serializer.save(user=user, status=Favorite.Status.VISIBLE)

    @action(detail=True, methods=["patch"], url_path="hide")
    def hide(self, request, pk=None):
        review = self.get_object()
        review.status = Favorite.Status.HIDDEN
        review.save()
        return Response(self.get_serializer(review).data)

    @action(detail=True, methods=["patch"], url_path="reveal")
    def reveal(self, request, pk=None):
        review = self.get_object()
        review.status = Favorite.Status.VISIBLE
        review.save()
        return Response(self.get_serializer(review).data)