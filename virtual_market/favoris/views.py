from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.permisions import IsAdminOrSuperAdmin
from admin.pagination import AdminPageNumberPagination
from notification.utils import notify_admins
from commande.models import Order, OrderItem
from .models import Favorite, Review, ReviewReport
from .serializers import FavoriteSerializer, ReviewSerializer


def is_moderator(user) -> bool:
    return user.is_authenticated and (
        user.is_superuser or user.role in ("admin", "superadmin")
    )


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
        # Les champs historiques de notation sur Favorite sont conservés pour
        # compatibilité ; les évaluations sont stockées dans Review.
        serializer.save(user=user, stars=1, comment="", status=Favorite.Status.VISIBLE)


class ReviewViewSet(viewsets.ModelViewSet):
    """Avis laissés sur les produits par les clients ET les vendeurs.

    Stockés dans la table `Review` : les favoris restent une table distincte.

    Lecture
      - `GET /?product=<id>` : avis visibles d'un produit → public (vitrine) ;
      - `GET /` : ses propres avis, ou tous pour un administrateur ;
      - `POST /<id>/report/` : signale un avis → notification admin.

    Écriture
      - un seul avis par utilisateur et par produit ;
      - impossible de noter son propre produit ;
      - un avis ne se modifie ou se supprime que par son auteur.
    """

    serializer_class = ReviewSerializer
    queryset = (
        Review.objects.select_related("user", "product__owner")
        .order_by("-created_at")
    )
    pagination_class = AdminPageNumberPagination

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            # La vitrine affiche les avis sans exiger de compte.
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

        if is_moderator(user):
            return qs

        if self.action in ("list", "retrieve"):
            product = self.request.query_params.get("product")
            if product:
                if not product.isdigit():
                    return qs.none()
                # Vitrine : uniquement les avis visibles du produit demandé.
                return qs.filter(status=Review.Status.VISIBLE, product=product, verified_purchase=True)
            if user.is_authenticated:
                # Sans filtre : « mes avis » (édition / suppression du sien).
                return qs.filter(user=user)
            return qs.none()

        if self.action == "report":
            # On signale un avis déjà publié (le sien est rejeté dans l'action).
            return qs.filter(status=Review.Status.VISIBLE, verified_purchase=True)

        # Écriture : uniquement ses propres avis, quel que soit le paramètre de
        # requête → 404 sur l'avis d'un autre auteur.
        return qs.filter(user=user) if user.is_authenticated else qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data["product"]
        if product.owner_id == user.id:
            raise ValidationError("Vous ne pouvez pas noter votre propre produit.")
        if Review.objects.filter(user=user, product=product).exists():
            raise ValidationError("Vous avez déjà laissé un avis pour ce produit.")
        if not OrderItem.objects.filter(
            order__user=user,
            order__status=Order.Status.COMPLETED,
            product=product,
        ).exists():
            raise ValidationError("Un achat livré est nécessaire pour publier un avis.")
        serializer.save(user=user, status=Review.Status.VISIBLE, verified_purchase=True)

    @action(detail=True, methods=["post"], url_path="report")
    def report(self, request, pk=None):
        review = self.get_object()
        if review.user_id == request.user.id:
            raise ValidationError("Vous ne pouvez pas signaler votre propre avis.")

        # Un signalement par couple (signalant, avis) : la notification part à
        # la première, les suivants servent de trace sans spammer les admins.
        _report, created = ReviewReport.objects.get_or_create(
            user=request.user, review=review
        )
        from admin.models import PlatformSettings

        platform = PlatformSettings.load()
        should_hide = (
            bool(platform.moderation.get("hideReportedReviews", False))
            and review.reports.count() >= 3
        )
        if should_hide and review.status != Review.Status.HIDDEN:
            review.status = Review.Status.HIDDEN
            review.save(update_fields=["status"])

        notified = 0
        if created and platform.notifications.get("newReportedReview", True):
            notified = notify_admins(
                title="Avis signalé",
                message=(
                    f"{request.user.username} a signalé l'avis de {review.user.username} "
                    f"sur « {review.product.name} » ({review.stars}/5)."
                ),
            )
        return Response(
            {
                "hidden": review.status == Review.Status.HIDDEN,
                "reported": True,
                "notified": notified,
                "detail": "Merci ! Notre équipe va examiner cet avis.",
            }
        )

    @action(detail=True, methods=["patch"], url_path="hide")
    def hide(self, request, pk=None):
        review = self.get_object()
        review.status = Review.Status.HIDDEN
        review.save()
        return Response(self.get_serializer(review).data)

    @action(detail=True, methods=["patch"], url_path="reveal")
    def reveal(self, request, pk=None):
        review = self.get_object()
        review.status = Review.Status.VISIBLE
        review.save()
        return Response(self.get_serializer(review).data)
