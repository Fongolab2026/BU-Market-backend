from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.contrib.auth.models import AbstractUser
from categorie.models import Category

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "superadmin","Super Admin"
        ADMIN = "admin","Admin"
        BUYER = "buyer", "Buyer"
        SELLER = "seller","Seller"

    class AccountStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "En attente"
        SUSPENDED = "suspended", "Suspendue"

    class ShopStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        VALIDATED = "validated", "Validée"
        SUSPENDED = "suspended", "Suspendue"

    role = models.CharField(choices=Role.choices, default=Role.BUYER)
    phone = models.CharField(max_length=20, blank=True, default="")
    adresse = models.CharField(max_length=200, blank=True, default="")
    profile_pic = models.ImageField(upload_to="image/", blank=True, null=True)
    is_active = models.BooleanField( default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    last_active = models.DateTimeField(blank=True, null=True)

    shop_name = models.CharField(max_length=100, blank=True, default="")
    shop_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shops",
    )
    shop_description = models.TextField(blank=True, default="")
    shop_image = models.ImageField(upload_to="shops/", blank=True, null=True)
    shop_views = models.PositiveIntegerField(default=0)
    shop_status = models.CharField(
        max_length=20,
        choices=ShopStatus.choices,
        default=ShopStatus.PENDING,
    )

    class Meta(AbstractUser.Meta):
        constraints = [
            # Une adresse e-mail ne peut appartenir qu'à un seul compte
            # (comparaison insensible à la casse). Les comptes sans e-mail
            # restent autorisés.
            models.UniqueConstraint(
                Lower("email"),
                condition=~Q(email=""),
                name="unique_email_ci",
            ),
            # Un numéro de téléphone ne peut être rattaché qu'à un seul compte.
            # Les comptes sans téléphone (valeur vide) restent autorisés.
            models.UniqueConstraint(
                fields=["phone"],
                condition=~Q(phone=""),
                name="unique_phone",
            ),
        ]

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

    @property
    def shop_display_name(self):
        return self.shop_name or self.username

    def _shop_review_notes(self):
        """Notes visibles attribuées à la boutique.

        Deux sources distinctes : les avis laissés sur ses produits
        (`favoris.Review`) et les avis laissés sur la boutique elle-même
        (`shops.ShopReview`).
        """
        from favoris.models import Review
        from shops.models import ShopReview

        product_notes = Review.objects.filter(
            product__owner=self, status=Review.Status.VISIBLE
        ).values_list("stars", flat=True)
        shop_notes = ShopReview.objects.filter(
            shop=self, status=ShopReview.Status.VISIBLE
        ).values_list("stars", flat=True)
        return list(product_notes) + list(shop_notes)

    def shop_rating(self):
        notes = self._shop_review_notes()
        return sum(notes) / len(notes) if notes else None

    def shop_review_count(self):
        return len(self._shop_review_notes())
