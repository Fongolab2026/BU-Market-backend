from django.db import models
from users.models import User
# Create your models here.
class Categories(models.Model):
    name = models.CharField(max_length= 100)

    def __str__(self):
        return self.name


class Products(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits= 10, decimal_places=2)
    categories = models.ForeignKey(
        Categories,
        on_delete=models.CASCADE
        )
    details = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

