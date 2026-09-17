from django.contrib import admin

from .models import Bill, BillItem


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    readonly_fields = ("item_type", "name", "quantity", "unit", "unit_price", "total_price")


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("bill_number", "shop_name", "customer_name", "bill_date", "grand_total", "created_at")
    search_fields = (
        "bill_number",
        "shop_name",
        "customer_name",
        "gst_number",
        "shop_address",
        "customer_address",
        "shop_phone",
        "customer_phone",
    )
    inlines = [BillItemInline]
    readonly_fields = (
        "bill_number",
        "subtotal",
        "gst_amount",
        "gst_percent",
        "adjustment_total",
        "grand_total",
        "created_at",
    )
