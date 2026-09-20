from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bills", "0004_bill_standard_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="bill_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bill",
            name="receipt_template",
            field=models.CharField(
                choices=[
                    ("invoice", "Standard Invoice"),
                    ("tax_invoice", "Tax Invoice"),
                    ("thermal", "Thermal Cash Memo"),
                ],
                default="invoice",
                max_length=16,
            ),
        ),
    ]
