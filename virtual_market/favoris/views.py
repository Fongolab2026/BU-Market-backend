from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.permisions import IsAdminOrSuperAdmin
from admin.pagination import AdminPageNumberPagination
from notification.utils import notify_admins
from .models import Favorite
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
        # Un favori ne porte pas de note ni de texte : c'est la présence d'un
        # commentaire qui transforme la ligne en avis (voir `reviews()`).
        serializer.save(user=user, stars=1, comment="", status=Favorite.Status.VISIBLE)


class ReviewViewSet(viewsets.ModelViewSet):
    """Avis laissés sur les produits par les clients ET les vendeurs.

    Lecture
      - `GET /?product=<id>` : avis visibles d'un produit → public (vitrine) ;
      - `GET /` : ses propres avis, ou tous pour un administrateur ;
      - `POST /<id>/report/` : signale un avis → notification admin.

    Écriture
      - un seul avis par utilisateur et par produit ;
      - le favori existant est « promu » en avis (même ligne en base) ;
      - impossible de noter son propre produit.
    """

    serializer_class = ReviewSerializer
    queryset = (
        Favorite.objects.reviews()
        .select_related("user", "product__owner")
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

        product = self.request.query_params.get("product")
        if product:
            if not product.isdigit():
                return qs.none()
            # Vitrine : uniquement les avis visibles du produit demandé.
            return qs.filter(status=Favorite.Status.VISIBLE, product=product)
        if self.action == "report":
            # On signale un avis déjà publié, pas le sien (filtré ensuite).
            return qs.filter(status=Favorite.Status.VISIBLE)
        if user.is_authenticated:
            # Sans filtre : « mes avis » (édition / suppression du sien).
            return qs.filter(user=user)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data["product"]
        if product.owner_id == user.id:
            raise ValidationError("Vous ne pouvez pas noter votre propre produit.")

        existing = Favorite.objects.filter(user=user, product=product).first()
        if existing and existing.comment:
            raise ValidationError("Vous avez déjà laissé un avis pour ce produit.")
        if existing:
            # Le produit était déjà favori : on transforme la ligne en avis
            # (unique_together user/product interdit d'en créer une seconde).
            for field, value in serializer.validated_data.items():
                setattr(existing, field, value)
            existing.status = Favorite.Status.VISIBLE
            existing.save()
            # Sans instance, `serializer.data` retomberait sur les données
            # brutes de la requête (dict) et planterait la sérialisation.
            serializer.instance = existing
        else:
            serializer.save(user=user, status=Favorite.Status.VISIBLE)

    @action(detail=True, methods=["post"], url_path="report")
    def report(self, request, pk=None):
        review = self.get_object()
        if review.user_id == request.user.id:
            raise ValidationError("Vous ne pouvez pas signaler votre propre avis.")
        notified = notify_admins(
            title="Avis signalé",
            message=(
                f"{request.user.username} a signalé l'avis de {review.user.username} "
                f"sur « {review.product.name} » ({review.stars}/5)."
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
        review.status = Favorite.Status.HIDDEN
        review.save()
        return Response(self.get_serializer(review).data)

    @action(detail=True, methods=["patch"], url_path="reveal")
    def reveal(self, request, pk=None):
        review = self.get_object()
        review.status = Favorite.Status.VISIBLE
        review.save()
        return Response(self.get_serializer(review).data)
