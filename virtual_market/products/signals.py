from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product


@receiver(post_save, sender=Product)
def handle_out_of_stock(sender, instance, **kwargs):
    """Retire automatiquement du catalogue un produit dont le stock est épuisé
    et prévient son vendeur dans son espace personnel.

    Un produit publié (``active``) sans stock ne doit pas être visible par les
    clients : on le bascule en ``inactive`` et on crée une notification pour le
    propriétaire.
    """
    if instance.status != Product.Status.ACTIVE or instance.stock > 0:
        return

    # ``update()`` évite de redéclencher le signal (pas de récursion).
    Product.objects.filter(pk=instance.pk).update(status=Product.Status.INACTIVE)
    instance.status = Product.Status.INACTIVE

    # Import local pour éviter tout souci d'ordre de chargement des apps.
    from notification.models import Notification

    Notification.objects.create(
        user=instance.owner,
        title="Rupture de stock",
        message=(
            f"Le stock du produit « {instance.name} » est épuisé. "
            "Il a été automatiquement retiré du catalogue. "
            "Ajoutez du stock puis réactivez-le pour le remettre en vente."
        ),
        type=Notification.Type.ALERT,
    )
