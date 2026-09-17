from django.db import models


class Bill(models.Model):
    DATE_FIXED = "fixed"
    DATE_MONTHLY = "monthly"
    DATE_RANDOM = "random"
    DATE_MODE_CHOICES = [
        (DATE_FIXED, "Fixed"),
        (DATE_MONTHLY, "Monthly"),
        (DATE_RANDOM, "Random"),
    ]

    PAY_CASH = "cash"
    PAY_UPI = "upi"
    PAY_CARD = "card"
    PAYMENT_CHOICES = [
        (PAY_CASH, "Cash"),
        (PAY_UPI, "UPI"),
        (PAY_CARD, "Card"),
    ]

    shop_name = models.CharField(max_length=160)
    shop_address = models.CharField(max_length=255, blank=True)
    shop_phone = models.CharField(max_length=20, blank=True)
    gst_number = models.CharField(max_length=32, blank=True)
    customer_name = models.CharField(max_length=160)
    customer_address = models.CharField(max_length=255, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    payment_mode = models.CharField(max_length=8, choices=PAYMENT_CHOICES, default=PAY_CASH)
    bill_number = models.CharField(max_length=32, unique=True)
    date_mode = models.CharField(max_length=16, choices=DATE_MODE_CHOICES)
    bill_date = models.DateField()
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)
    adjustment_total = models.DecimalField(max_digits=12, decimal_places=2)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.bill_number} — {self.customer_name}"


class BillItem(models.Model):
    GROCERY = "grocery"
    ADJUSTMENT = "adjustment"
    ITEM_TYPE_CHOICES = [
        (GROCERY, "Grocery"),
        (ADJUSTMENT, "Adjustment"),
    ]

    bill = models.ForeignKey(Bill, related_name="items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=16, choices=ITEM_TYPE_CHOICES)
    name = models.CharField(max_length=160)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=16)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"
