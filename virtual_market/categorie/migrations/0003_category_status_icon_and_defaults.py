from django.db import migrations, models
from django.utils.text import slugify


DEFAULT_CATEGORIES = [
    ("Alimentation", "Produits alimentaires et boissons", "apple"),
    ("Mode & accessoires", "Vêtements, chaussures, accessoires", "shirt"),
    ("Artisanat", "Objets faits main et décoration", "wrench"),
    ("Maison & décoration", "Meubles, luminaires et décoration", "house"),
    ("Beauté & soins", "Cosmétiques, hygiène et bien-être", "sparkles"),
    ("Électronique", "Appareils et accessoires technologiques", "smartphone"),
]


def create_default_categories(apps, schema_editor):
    Category = apps.get_model("categorie", "Category")
    for name, description, icon in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            name=name,
            defaults={
                "slug": slugify(name),
                "description": description,
                "icon": icon,
                "active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("categorie", "0002_alter_category_id")]

    operations = [
        migrations.AddField(
            model_name="category",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="category",
            name="icon",
            field=models.CharField(default="package", max_length=40),
        ),
        migrations.RunPython(create_default_categories, migrations.RunPython.noop),
    ]