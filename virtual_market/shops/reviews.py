from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from admin.pagination import AdminPageNumberPagination
from notification.utils import notify_admins
from users.permisions import IsAdminOrSuperAdmin

from .models import ShopReview
from .serializers import ShopReviewSerializer


def _is_moderator(user) -> bool:
    return user.is_authenticated and (
        user.is_superuser or user.role in ("admin", "superadmin")
    )


class ShopReviewViewSet(viewsets.ModelViewSet):
    """Avis déposés sur les boutiques (clients ET vendeurs).

    Lecture
      - `GET /?shop=<id>` : avis visibles d'une boutique → public (modale
        boutique, profil vendeur) ;
      - `GET /` : ses propres avis, ou tous pour un administrateur.

    Écriture
      - un seul avis par couple (auteur, boutique) ;
      - impossible de noter sa propre boutique ;
      - la boutique notée doit être validée par l'administration.
    """

    serializer_class = ShopReviewSerializer
    queryset = ShopReview.objects.select_related("user", "shop").order_by(
        "-created_at"
    )
    pagination_class = AdminPageNumberPagination

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            permission_classes = [AllowAny]
        elif self.action in ("create", "update", "partial_update", "destroy", "report"):
            permission_classes = [IsAuthenticated]
        else:
            # hide / reveal : modération réservée à l'administration.
            permission_classes = [IsAdminOrSuperAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_moderator(user):
            return qs

        shop = self.request.query_params.get("shop")
        if shop:
            if not shop.isdigit():
                return qs.none()
            return qs.filter(status=ShopReview.Status.VISIBLE, shop=shop)
        if self.action == "report":
            return qs.filter(status=ShopReview.Status.VISIBLE)
        if user.is_authenticated:
            return qs.filter(user=user)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        shop = serializer.validated_data["shop"]
        if shop.pk == user.pk:
            raise ValidationError("Vous ne pouvez pas noter votre propre boutique.")
        if ShopReview.objects.filter(user=user, shop=shop).exists():
            raise ValidationError("Vous avez déjà laissé un avis pour cette boutique.")
        serializer.save(user=user, status=ShopReview.Status.VISIBLE)

    @action(detail=True, methods=["post"], url_path="report")
    def report(self, request, pk=None):
        review = self.get_object()
        if review.user_id == request.user.id:
            raise ValidationError("Vous ne pouvez pas signaler votre propre avis.")
        notified = notify_admins(
            title="Avis boutique signalé",
            message=(
                f"{request.user.username} a signalé l'avis de {review.user.username} "
                f"sur la boutique « {review.shop.shop_display_name} » "
                f"({review.stars}/5)."
            ),
        )
        return Response(
            {
                "hidden": False,
                "reported": True,
                "notified": notified,
                "detail": "Merci ! Notre équipe va examiner cet avis.",
            }
        )

    @action(detail=True, methods=["patch"], url_path="hide")
    def hide(self, request, pk=None):
        review = self.get_object()
        review.status = ShopReview.Status.HIDDEN
        review.save(update_fields=["status"])
        return Response(self.get_serializer(review).data)

    @action(detail=True, methods=["patch"], url_path="reveal")
    def reveal(self, request, pk=None):
        review = self.get_object()
        review.status = ShopReview.Status.VISIBLE
        review.save(update_fields=["status"])
        return Response(self.get_serializer(review).data)
