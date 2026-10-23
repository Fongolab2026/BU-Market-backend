from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product


@receiver(post_save, sender=Product)
def handle_out_of_stock(sender, instance, **kwargs):
    """Notify the seller and permanently remove products with no stock."""
    if instance.stock > 0:
        return

    # Import local pour éviter tout souci d'ordre de chargement des apps.
    from notification.models import Notification

    Notification.objects.create(
        user=instance.owner,
        title="Rupture de stock",
        message=(
            f"Le stock du produit « {instance.name} » est épuisé. "
            "Le produit a été supprimé du catalogue et de la base de données."
        ),
        type=Notification.Type.ALERT,
    )
    # OrderItem uses SET_NULL and keeps product, shop, price, and image
    # Keep uploaded image files in storage: order items may still reference
    # their saved path after ProductImage rows are cascaded away.
    instance.delete()
