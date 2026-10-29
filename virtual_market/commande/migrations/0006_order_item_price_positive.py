import decimal
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("commande", "0005_product_snapshots_and_nullable_product")]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[MinValueValidator(decimal.Decimal("0.01"))],
            ),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(
                condition=models.Q(("price__gt", 0)),
                name="order_item_price_positive",
            ),
        ),
    ]
