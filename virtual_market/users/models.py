from django.db import models
from django.db.models import Avg
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
    shop_views = models.PositiveIntegerField(default=0)
    shop_status = models.CharField(
        max_length=20,
        choices=ShopStatus.choices,
        default=ShopStatus.PENDING,
    )

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

    @property
    def shop_display_name(self):
        return self.shop_name or self.username

    def shop_rating(self):
        from favoris.models import Favorite
        return (
            Favorite.objects.filter(product__owner=self)
            .aggregate(avg=Avg("stars"))["avg"]
        )

    def shop_review_count(self):
        from favoris.models import Favorite
        return Favorite.objects.filter(product__owner=self).count()