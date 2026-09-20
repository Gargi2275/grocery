from rest_framework import serializers

from decimal import Decimal

from .models import Bill, BillItem


class BillItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillItem
        fields = (
            "id",
            "item_type",
            "name",
            "quantity",
            "unit",
            "unit_price",
            "total_price",
        )


class BillSerializer(serializers.ModelSerializer):
    items = BillItemSerializer(many=True, read_only=True)
    grocery_items = serializers.SerializerMethodField()
    adjustment_items = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = (
            "id",
            "shop_name",
            "shop_address",
            "shop_phone",
            "gst_number",
            "customer_name",
            "customer_address",
            "customer_phone",
            "payment_mode",
            "bill_number",
            "date_mode",
            "bill_date",
            "bill_time",
            "receipt_template",
            "max_amount",
            "gst_percent",
            "subtotal",
            "gst_amount",
            "adjustment_total",
            "grand_total",
            "created_at",
            "items",
            "grocery_items",
            "adjustment_items",
        )

    def get_grocery_items(self, obj):
        return BillItemSerializer(
            [item for item in obj.items.all() if item.item_type == BillItem.GROCERY],
            many=True,
        ).data

    def get_adjustment_items(self, obj):
        return BillItemSerializer(
            [item for item in obj.items.all() if item.item_type == BillItem.ADJUSTMENT],
            many=True,
        ).data


class BillListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = (
            "id",
            "shop_name",
            "customer_name",
            "bill_number",
            "bill_date",
            "bill_time",
            "receipt_template",
            "grand_total",
            "gst_percent",
            "created_at",
        )


class SelectedProductSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True)


class GenerateBillSerializer(serializers.Serializer):
    shop_name = serializers.CharField(max_length=160)
    shop_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shop_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    gst_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    customer_name = serializers.CharField(max_length=160)
    customer_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    payment_mode = serializers.ChoiceField(
        choices=[c[0] for c in Bill.PAYMENT_CHOICES], required=False, default=Bill.PAY_CASH
    )
    max_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    date_mode = serializers.ChoiceField(choices=[c[0] for c in Bill.DATE_MODE_CHOICES])
    bill_date = serializers.DateField(required=False, allow_null=True)
    date_range_start = serializers.DateField(required=False, allow_null=True)
    date_range_end = serializers.DateField(required=False, allow_null=True)
    product_mode = serializers.ChoiceField(choices=["random", "select"], default="random")
    selected_products = SelectedProductSerializer(many=True, required=False)
    count = serializers.IntegerField(min_value=1, max_value=25, default=1, required=False)
    apply_gst = serializers.BooleanField(required=False, default=True)
    gst_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, default=Decimal("5.00")
    )
    receipt_template = serializers.ChoiceField(
        choices=[c[0] for c in Bill.TEMPLATE_CHOICES],
        required=False,
        default=Bill.TEMPLATE_INVOICE,
    )

    def validate(self, attrs):
        if attrs.get("product_mode") == "select" and not attrs.get("selected_products"):
            raise serializers.ValidationError(
                {"selected_products": "Select at least one product."}
            )
        if not attrs.get("apply_gst", True):
            attrs["gst_percent"] = Decimal("0.00")
        percent = attrs.get("gst_percent")
        if percent is None:
            attrs["gst_percent"] = Decimal("5.00")
        elif percent < 0 or percent > 40:
            raise serializers.ValidationError(
                {"gst_percent": "GST percent must be between 0 and 40."}
            )
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
