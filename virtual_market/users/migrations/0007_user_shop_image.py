from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0006_alter_user_id")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="shop_image",
            field=models.ImageField(blank=True, null=True, upload_to="shops/"),
        ),
    ]
