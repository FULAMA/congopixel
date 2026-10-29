# Generated for configurable per-variant stock alerts.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_productimage_thumb")]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="low_stock_threshold",
            field=models.PositiveIntegerField(
                default=3,
                help_text="Alerte lorsque le stock disponible est inférieur ou égal à ce seuil.",
                verbose_name="seuil de stock bas",
            ),
        ),
    ]
