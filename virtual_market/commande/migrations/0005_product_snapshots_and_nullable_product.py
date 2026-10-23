import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def save_order_item_snapshots(apps, schema_editor):
    OrderItem = apps.get_model("commande", "OrderItem")
    ProductImage = apps.get_model("products", "ProductImage")
    for item in OrderItem.objects.select_related("product").iterator():
        product = item.product
        if product is None:
            continue
        owner = product.owner
        main_image = (
            ProductImage.objects.filter(product_id=product.pk, is_main=True).first()
            or ProductImage.objects.filter(product_id=product.pk).first()
        )
        item.product_name = product.name
        item.shop_name = owner.shop_name or owner.username
        item.seller_id = owner.pk
        item.product_image_key = main_image.image.name if main_image else ""
        item.save(
            update_fields=[
                "product_name",
                "shop_name",
                "seller",
                "product_image_key",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("commande", "0004_alter_order_status"),
        ("products", "0007_alter_product_details"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="product_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="shop_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="product_image_key",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="seller",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sold_order_items",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(save_order_item_snapshots, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="orderitem",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="order_items",
                to="products.product",
            ),
        ),
    ]
