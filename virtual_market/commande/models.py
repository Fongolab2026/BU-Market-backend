from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator
from decimal import Decimal
from products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmée"
        SHIPPED = "shipped", "Expédiée"
        COMPLETED = "completed", "Livrée"
        CANCELLED = "cancelled", "Annulée"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_orders",
    )
    server = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="served_orders",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        return f"Commande {self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    # Snapshots keep completed order history readable after an exhausted
    # product is permanently removed from the catalog.
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sold_order_items",
    )
    product_name = models.CharField(max_length=150, blank=True, default="")
    shop_name = models.CharField(max_length=150, blank=True, default="")
    product_image_key = models.CharField(max_length=500, blank=True, default="")
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name="order_item_price_positive",
            )
        ]

    def save(self, *args, **kwargs):
        if self.product_id:
            product = self.product
            if not self.product_name:
                self.product_name = product.name
            if not self.shop_name and product.owner_id:
                self.shop_name = product.owner.shop_display_name
            if not self.seller_id:
                self.seller_id = product.owner_id
            if not self.product_image_key:
                images = list(product.images.all())
                main = next((image for image in images if image.is_main), None)
                if main is None and images:
                    main = images[0]
                if main and main.image:
                    self.product_image_key = main.image.name
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product_name or (self.product.name if self.product else 'Produit supprimé')}"
