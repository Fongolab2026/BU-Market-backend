from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from products.models import Product


class FavoriteQuerySet(models.QuerySet):
    """Sous-ensemble des lignes `Favorite` qui portent encore un commentaire.

    Les avis vivent désormais dans la table `Review` (voir `favoris.Review`) ;
    ce filtre reste pour lire d'éventuelles lignes historiques copiées avant
    la migration `0004_copy_commented_reviews`.
    """

    def reviews(self):
        return self.exclude(comment="").exclude(comment__isnull=True)


class Favorite(models.Model):
    class Status(models.TextChoices):
        VISIBLE = "visible", "Visible"
        HIDDEN = "hidden", "Masqué"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    stars = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note en étoiles de 1 à 5",
    )
    comment = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VISIBLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FavoriteQuerySet.as_manager()

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"

    def __str__(self):
        return f"{self.user.username} aime {self.product.name}"


class Review(models.Model):
    class Status(models.TextChoices):
        VISIBLE = "visible", "Visible"
        HIDDEN = "hidden", "Masqué"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_reviews",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note en étoiles de 1 à 5",
    )
    comment = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VISIBLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_product_review_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.username} a noté {self.product.name} : {self.stars} étoile(s)"


class ReviewReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_reports",
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "review"], name="unique_review_report_per_user"
            )
        ]
