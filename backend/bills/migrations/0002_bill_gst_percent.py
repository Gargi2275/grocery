from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bills", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="gst_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("5.00"), max_digits=5),
        ),
        migrations.AlterField(
            model_name="bill",
            name="gst_number",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
