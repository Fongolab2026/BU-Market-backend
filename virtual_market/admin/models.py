from django.db import models


class PlatformSettings(models.Model):
    platform_name = models.CharField(max_length=100, default="BUJA MARKET")
    support_email = models.EmailField(default="support@buja.market")
    phone = models.CharField(max_length=20, blank=True, default="")
    default_language = models.CharField(max_length=10, default="fr")
    currency = models.CharField(max_length=10, default="BIF")
    moderation = models.JSONField(default=dict, blank=True)
    notifications = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Paramètres de la plateforme"
        verbose_name_plural = "Paramètres de la plateforme"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.platform_name