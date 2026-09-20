from django.db import models
from users.models import User
from categorie.models import Category
# Create your views here.
class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
        )
    details = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def date(self):
        return self.created_at

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
        )
    image = models.ImageField(upload_to="products/")
    is_main = models.BooleanField(default=False, verbose_name="Image principale")

    class Meta:
        verbose_name = "Image produit"
        verbose_name_plural = "Images produits"

    def __str__(self):
        return f"{self.product.name} ({'principale' if self.is_main else 'secondaire'})"