from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bills", "0002_bill_gst_percent"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="shop_address",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="bill",
            name="customer_address",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
