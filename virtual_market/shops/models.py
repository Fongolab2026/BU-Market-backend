from django.conf import settings
from django.db import models


class Boutique(models.Model):
    """Demande de location d'espace remplie via la page /louer-espace."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        VALIDATED = "validated", "Validée"
        REJECTED = "rejected", "Rejetée"
        SUSPENDED = "suspended", "Suspendue"

    # Un commerçant ne peut posséder qu'une seule boutique (garanti par la BDD).
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="boutique",
        null=True,
        blank=True,
    )

    # --- Section « Boutique » ---
    company_name = models.CharField(max_length=150)
    owner_name = models.CharField(max_length=150)
    industry = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True, default="")
    slogan = models.CharField(max_length=200, blank=True, default="")

    # --- Section « Réseaux sociaux » ---
    facebook = models.URLField(max_length=300, blank=True, default="")
    instagram = models.URLField(max_length=300, blank=True, default="")
    tiktok = models.URLField(max_length=300, blank=True, default="")
    website = models.URLField(max_length=300, blank=True, default="")

    # --- Section « Emplacement » ---
    province = models.CharField(max_length=60)
    commune = models.CharField(max_length=60)
    neighborhood = models.CharField(max_length=100)
    other_neighborhood = models.CharField(max_length=100, blank=True, default="")

    # --- Suivi admin ---
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Boutique"
        verbose_name_plural = "Boutiques"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} - {self.province}/{self.commune}"
