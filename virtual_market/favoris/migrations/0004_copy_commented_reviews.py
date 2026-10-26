from django.db import migrations


def copy_commented_reviews(apps, schema_editor):
    Favorite = apps.get_model("favoris", "Favorite")
    Review = apps.get_model("favoris", "Review")
    for favorite in Favorite.objects.exclude(comment="").iterator():
        review, created = Review.objects.get_or_create(
            user_id=favorite.user_id,
            product_id=favorite.product_id,
            defaults={
                "stars": favorite.stars,
                "comment": favorite.comment,
                "status": favorite.status,
            },
        )
        if created:
            Review.objects.filter(pk=review.pk).update(created_at=favorite.created_at)


class Migration(migrations.Migration):
    dependencies = [
        ("favoris", "0003_review"),
    ]

    operations = [
        migrations.RunPython(copy_commented_reviews, migrations.RunPython.noop),
    ]
