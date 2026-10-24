from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.permisions import IsAdminOrSuperAdmin
from admin.pagination import AdminPageNumberPagination
from .models import Favorite, Review, ReviewReport
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
        # Les champs historiques de notation sur Favorite sont conservés pour
        # compatibilité ; les évaluations sont stockées dans Review.
        serializer.save(user=user, stars=1, comment="", status=Favorite.Status.VISIBLE)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related("user", "product__owner").order_by("-created_at")
    pagination_class = AdminPageNumberPagination

    def get_permissions(self):
        if self.action in ("create", "list", "retrieve", "report"):
            # Les acheteurs peuvent créer/lire leurs avis
            permission_classes = [IsAuthenticated]
        else:
            # hide/reveal/update/delete réservés aux admins
            permission_classes = [IsAdminOrSuperAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ("admin", "superadmin"):
            qs = self.queryset
        else:
            # Les acheteurs peuvent lire les avis visibles du catalogue.
            qs = self.queryset.filter(status=Review.Status.VISIBLE)
        product_id = self.request.query_params.get("product")
        if product_id and product_id.isdigit():
            qs = qs.filter(product_id=int(product_id))
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data["product"]
        if Review.objects.filter(user=user, product=product).exists():
            raise ValidationError("Vous avez déjà laissé un avis pour ce produit.")
        serializer.save(user=user, status=Review.Status.VISIBLE)

    @action(detail=True, methods=["post"], url_path="report")
    def report(self, request, pk=None):
        review = self.get_object()
        if review.user_id == request.user.pk:
            raise ValidationError("Vous ne pouvez pas signaler votre propre avis.")

        report, created = ReviewReport.objects.get_or_create(
            user=request.user, review=review
        )
        from admin.models import PlatformSettings
        from notification.models import Notification
        from users.models import User

        settings = PlatformSettings.load()
        should_hide = settings.moderation.get("hideReportedReviews", False)
        if should_hide and review.status != Review.Status.HIDDEN:
            review.status = Review.Status.HIDDEN
            review.save(update_fields=["status"])

        if created and settings.notifications.get("newReportedReview", False):
            admins = User.objects.filter(role__in=("admin", "superadmin"))
            Notification.objects.bulk_create([
                Notification(
                    user=admin,
                    title="Nouvel avis signalé",
                    message=f"L’avis sur « {review.product.name} » a été signalé.",
                    type=Notification.Type.ALERT,
                )
                for admin in admins
            ])
        return Response({"reported": True, "hidden": should_hide})

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
