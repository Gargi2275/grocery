"""Editable grocery/adjustment catalogues and GST rate.

Update prices here — no migration required.
"""

from decimal import Decimal

GST_RATE = Decimal("0.05")  # 5% GST on grocery items only

# qty_options are typical kirana purchase sizes for each SKU.
GROCERY_ITEMS = [
    {"name": "Basmati Rice", "unit": "kg", "unit_price": Decimal("100.00"), "qty_options": ["0.5", "1", "2", "5"]},
    {"name": "Sona Masuri Rice", "unit": "kg", "unit_price": Decimal("46.50"), "qty_options": ["1", "2", "5"]},
    {"name": "Wheat Atta", "unit": "kg", "unit_price": Decimal("37.48"), "qty_options": ["1", "2", "5", "10"]},
    {"name": "Toor Dal", "unit": "kg", "unit_price": Decimal("124.24"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Moong Dal", "unit": "kg", "unit_price": Decimal("112.16"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Chana Dal", "unit": "kg", "unit_price": Decimal("88.13"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Urad Dal", "unit": "kg", "unit_price": Decimal("122.64"), "qty_options": ["0.5", "1"]},
    {"name": "Masoor Dal", "unit": "kg", "unit_price": Decimal("90.74"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Sunflower Oil", "unit": "ltr", "unit_price": Decimal("193.48"), "qty_options": ["0.5", "1", "2", "5"]},
    {"name": "Mustard Oil", "unit": "ltr", "unit_price": Decimal("202.52"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Groundnut Oil", "unit": "ltr", "unit_price": Decimal("209.08"), "qty_options": ["0.5", "1"]},
    {"name": "Sugar", "unit": "kg", "unit_price": Decimal("58.66"), "qty_options": ["0.5", "1", "2", "5"]},
    {"name": "Iodized Salt", "unit": "kg", "unit_price": Decimal("22.25"), "qty_options": ["1", "2"]},
    {"name": "Turmeric Powder", "unit": "kg", "unit_price": Decimal("334.00"), "qty_options": ["0.1", "0.2", "0.25"]},
    {"name": "Red Chilli Powder", "unit": "kg", "unit_price": Decimal("304.20"), "qty_options": ["0.1", "0.2", "0.25"]},
    {"name": "Coriander Powder", "unit": "kg", "unit_price": Decimal("175.08"), "qty_options": ["0.1", "0.2", "0.25"]},
    {"name": "Garam Masala", "unit": "kg", "unit_price": Decimal("850.00"), "qty_options": ["0.05", "0.1"]},
    {"name": "Tea Leaf", "unit": "kg", "unit_price": Decimal("275.27"), "qty_options": ["0.1", "0.25", "0.5"]},
    {"name": "Instant Coffee", "unit": "kg", "unit_price": Decimal("4000.00"), "qty_options": ["0.05", "0.1", "0.2"]},
    {"name": "Toned Milk", "unit": "ltr", "unit_price": Decimal("61.24"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Bread Loaf", "unit": "pcs", "unit_price": Decimal("48.00"), "qty_options": ["1", "2"]},
    {"name": "Onion", "unit": "kg", "unit_price": Decimal("53.78"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Potato", "unit": "kg", "unit_price": Decimal("22.72"), "qty_options": ["0.5", "1", "2", "5"]},
    {"name": "Tomato", "unit": "kg", "unit_price": Decimal("38.77"), "qty_options": ["0.5", "1", "2"]},
    {"name": "Green Chilli", "unit": "kg", "unit_price": Decimal("58.00"), "qty_options": ["0.1", "0.25", "0.5"]},
    {"name": "Banana", "unit": "pcs", "unit_price": Decimal("6.20"), "qty_options": ["6", "12"]},
    {"name": "Apple", "unit": "kg", "unit_price": Decimal("160.00"), "qty_options": ["0.5", "1"]},
    {"name": "Marie Biscuits", "unit": "pcs", "unit_price": Decimal("35.00"), "qty_options": ["1", "2", "3"]},
    {"name": "Bath Soap", "unit": "pcs", "unit_price": Decimal("40.00"), "qty_options": ["1", "2", "4"]},
    {"name": "Detergent Powder", "unit": "kg", "unit_price": Decimal("95.00"), "qty_options": ["0.5", "1", "2"]},
]

ADJUSTMENT_ITEMS = [
    {"name": "Chocolate Eclair", "unit": "pcs", "unit_price": Decimal("2.00")},
    {"name": "Paan", "unit": "pcs", "unit_price": Decimal("15.00")},
    {"name": "Chewing Gum", "unit": "pcs", "unit_price": Decimal("5.00")},
    {"name": "Candy", "unit": "pcs", "unit_price": Decimal("1.00")},
    {"name": "Small Biscuit Packet", "unit": "pcs", "unit_price": Decimal("10.00")},
    {"name": "Toffee", "unit": "pcs", "unit_price": Decimal("2.00")},
    {"name": "Mentos", "unit": "pcs", "unit_price": Decimal("5.00")},
    {"name": "Lollipop", "unit": "pcs", "unit_price": Decimal("5.00")},
    {"name": "Mouth Freshener", "unit": "pcs", "unit_price": Decimal("10.00")},
    {"name": "Mini Chocolate Bar", "unit": "pcs", "unit_price": Decimal("20.00")},
]

MIN_QTY = {
    "kg": Decimal("0.05"),
    "g": Decimal("10"),
    "ltr": Decimal("0.25"),
    "ml": Decimal("50"),
    "pcs": Decimal("1"),
}

QTY_STEP = {
    "kg": Decimal("0.05"),
    "g": Decimal("10"),
    "ltr": Decimal("0.25"),
    "ml": Decimal("50"),
    "pcs": Decimal("1"),
}
