from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ShopReview(models.Model):
    """Avis déposé sur une boutique entière (par un client ou un autre vendeur).

    `shop` est le propriétaire de la boutique (un `User` de rôle `seller`),
    `user` l'auteur de l'avis. Un seul avis par couple (auteur, boutique).
    """

    class Status(models.TextChoices):
        VISIBLE = "visible", "Visible"
        HIDDEN = "hidden", "Masqué"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shop_reviews_written",
    )
    shop = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shop_reviews_received",
    )
    stars = models.PositiveSmallIntegerField(
        default=5,
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
        unique_together = ("user", "shop")
        ordering = ["-created_at"]
        verbose_name = "Avis de boutique"
        verbose_name_plural = "Avis de boutique"

    def __str__(self):
        return f"{self.user.username} → {self.shop.shop_display_name} : {self.stars}/5"


class BoutiqueRequest(models.Model):
    """Demande de location d'espace vendeur envoyée depuis /louer-espace."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        VALIDATED = "validated", "Validée"
        REJECTED = "rejected", "Rejetée"
        SUSPENDED = "suspended", "Suspendue"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="boutique_requests",
    )
    company_name = models.CharField(max_length=150)
    owner_name = models.CharField(max_length=150, blank=True, default="")
    industry = models.CharField(max_length=100, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    slogan = models.CharField(max_length=200, blank=True, default="")
    facebook = models.CharField(max_length=255, blank=True, default="")
    instagram = models.CharField(max_length=255, blank=True, default="")
    tiktok = models.CharField(max_length=255, blank=True, default="")
    website = models.CharField(max_length=255, blank=True, default="")
    province = models.CharField(max_length=100, blank=True, default="")
    commune = models.CharField(max_length=100, blank=True, default="")
    neighborhood = models.CharField(max_length=100, blank=True, default="")
    other_neighborhood = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande de boutique"
        verbose_name_plural = "Demandes de boutique"

    def __str__(self):
        return f"{self.company_name} ({self.get_status_display()})"
