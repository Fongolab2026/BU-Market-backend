from django.conf import settings
from django.db import models
from products.models import Product


class PublicationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvée"
        REJECTED = "rejected", "Rejetée"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="publication_requests",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="publication_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Publication {self.product.name} - {self.seller.username}"