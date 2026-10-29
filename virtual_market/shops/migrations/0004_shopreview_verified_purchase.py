from django.db import migrations, models


def mark_verified_shop_reviews(apps, schema_editor):
    ShopReview = apps.get_model("shops", "ShopReview")
    OrderItem = apps.get_model("commande", "OrderItem")
    for review in ShopReview.objects.all().iterator():
        if OrderItem.objects.filter(
            order__user_id=review.user_id,
            order__status="completed",
            seller_id=review.shop_id,
        ).exists():
            ShopReview.objects.filter(pk=review.pk).update(verified_purchase=True)


class Migration(migrations.Migration):
    dependencies = [
        ("shops", "0003_shopreviewreport"),
        ("commande", "0005_product_snapshots_and_nullable_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="shopreview",
            name="verified_purchase",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_verified_shop_reviews, migrations.RunPython.noop),
    ]
