from django.db import migrations, models


def mark_verified_product_reviews(apps, schema_editor):
    Review = apps.get_model("favoris", "Review")
    OrderItem = apps.get_model("commande", "OrderItem")
    for review in Review.objects.all().iterator():
        if OrderItem.objects.filter(
            order__user_id=review.user_id,
            order__status="completed",
            product_id=review.product_id,
        ).exists():
            Review.objects.filter(pk=review.pk).update(verified_purchase=True)


class Migration(migrations.Migration):
    dependencies = [
        ("favoris", "0005_reviewreport"),
        ("commande", "0005_product_snapshots_and_nullable_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="verified_purchase",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_verified_product_reviews, migrations.RunPython.noop),
    ]
