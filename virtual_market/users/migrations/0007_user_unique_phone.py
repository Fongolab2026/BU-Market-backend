from django.db import migrations, models


def dedupe_phones(apps, schema_editor):
    """Vide les numéros en double en conservant le compte le plus ancien.

    Les comptes sans téléphone (chaîne vide) restent inchangés. C'est
    nécessaire avant d'ajouter la contrainte d'unicité sur ``phone``.
    """
    User = apps.get_model("users", "User")
    seen = set()
    for user in User.objects.exclude(phone="").order_by("id"):
        if user.phone in seen:
            user.phone = ""
            user.save(update_fields=["phone"])
        else:
            seen.add(user.phone)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_user_unique_email_ci"),
    ]

    operations = [
        migrations.RunPython(dedupe_phones, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=("phone",),
                condition=models.Q(("phone", ""), _negated=True),
                name="unique_phone",
            ),
        ),
    ]
