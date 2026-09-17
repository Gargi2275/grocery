from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bills", "0003_bill_addresses"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="shop_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="bill",
            name="customer_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="bill",
            name="payment_mode",
            field=models.CharField(
                choices=[("cash", "Cash"), ("upi", "UPI"), ("card", "Card")],
                default="cash",
                max_length=8,
            ),
        ),
    ]
