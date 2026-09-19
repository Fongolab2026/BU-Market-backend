from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "superadmin","Super Admin"
        ADMIN = "admin","Admin"
        BUYER = "buyer", "Buyer"
        SELLER = "seller","Seller"

    role = models.CharField(choices=Role.choices, default=Role.BUYER)
    phone = models.CharField( max_length=20)
    adresse = models.CharField(max_length=200)
    profile_pic = models.ImageField(upload_to="image/", blank=True, null=True)
    is_active = models.BooleanField( default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)


