from __future__ import annotations

import calendar
import random
import re
import secrets
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from .catalog import adjustment_catalog, grocery_catalog
from .constants import GST_RATE, MIN_QTY, QTY_STEP
from .models import Bill, BillItem

TWO_PLACES = Decimal("0.01")
THREE_PLACES = Decimal("0.001")


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _qty(value: Decimal) -> Decimal:
    return value.quantize(THREE_PLACES, rounding=ROUND_HALF_UP)


def _line_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return _money(quantity * unit_price)


def _gst_fraction(gst_percent: Decimal) -> Decimal:
    return (Decimal(gst_percent) / Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _totals(
    grocery: list[dict],
    adjustments: list[dict],
    gst_rate: Decimal = GST_RATE,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    subtotal = sum((item["total_price"] for item in grocery), Decimal("0.00"))
    gst_amount = _money(subtotal * gst_rate)
    adjustment_total = sum((item["total_price"] for item in adjustments), Decimal("0.00"))
    grand_total = _money(subtotal + gst_amount + adjustment_total)
    return _money(subtotal), gst_amount, _money(adjustment_total), grand_total


def _refresh_totals(items: list[dict]) -> None:
    for item in items:
        item["quantity"] = _qty(Decimal(item["quantity"]))
        item["unit_price"] = _money(Decimal(item["unit_price"]))
        item["total_price"] = _line_total(item["quantity"], item["unit_price"])


def _pick_grocery_lines(count: int) -> list[dict]:
    grocery = grocery_catalog()
    sample = deepcopy(random.sample(grocery, k=min(count, len(grocery))))
    lines = []
    for sku in sample:
        quantity = Decimal(random.choice(sku["qty_options"]))
        lines.append(
            {
                "item_type": BillItem.GROCERY,
                "name": sku["name"],
                "quantity": quantity,
                "unit": sku["unit"],
                "unit_price": sku["unit_price"],
                "total_price": _line_total(quantity, sku["unit_price"]),
                "max_qty": Decimal(max(sku["qty_options"])),
            }
        )
    return lines


def _pick_adjustment_lines(count: int) -> list[dict]:
    adjustments = adjustment_catalog()
    sample = deepcopy(random.sample(adjustments, k=min(count, len(adjustments))))
    lines = []
    for sku in sample:
        quantity = Decimal(random.randint(1, 3))
        lines.append(
            {
                "item_type": BillItem.ADJUSTMENT,
                "name": sku["name"],
                "quantity": quantity,
                "unit": sku["unit"],
                "unit_price": sku["unit_price"],
                "total_price": _line_total(quantity, sku["unit_price"]),
            }
        )
    return lines


def _catalog_lookup() -> dict[str, tuple[str, dict]]:
    lookup = {sku["name"]: (BillItem.GROCERY, sku) for sku in grocery_catalog()}
    lookup.update({sku["name"]: (BillItem.ADJUSTMENT, sku) for sku in adjustment_catalog()})
    return lookup


def _lines_from_selection(selected_products: list[dict]) -> tuple[list[dict], list[dict]]:
    lookup = _catalog_lookup()
    grocery: list[dict] = []
    adjustments: list[dict] = []
    seen: set[str] = set()

    for entry in selected_products:
        name = str(entry.get("name") or "").strip()
        if not name or name in seen:
            continue
        if name not in lookup:
            raise ValueError(f"Unknown product: {name}")

        item_type, sku = lookup[name]
        raw_qty = entry.get("quantity")
        if raw_qty is not None and str(raw_qty) != "":
            quantity = Decimal(str(raw_qty))
            if quantity <= 0:
                raise ValueError(f"Quantity for {name} must be greater than 0.")
        elif item_type == BillItem.GROCERY:
            quantity = Decimal(random.choice(sku["qty_options"]))
        else:
            quantity = Decimal(random.randint(1, 3))

        line = {
            "item_type": item_type,
            "name": sku["name"],
            "quantity": quantity,
            "unit": sku["unit"],
            "unit_price": sku["unit_price"],
            "total_price": _line_total(quantity, sku["unit_price"]),
        }
        if item_type == BillItem.GROCERY:
            max_qty = Decimal(max(sku["qty_options"]))
            line["max_qty"] = max(max_qty, quantity)
            grocery.append(line)
        else:
            adjustments.append(line)
        seen.add(name)

    if not grocery:
        raise ValueError("Select at least one grocery product.")
    return grocery, adjustments


def _reduce_line(item: dict) -> bool:
    unit = item["unit"]
    step = QTY_STEP.get(unit, Decimal("1"))
    minimum = MIN_QTY.get(unit, Decimal("1"))
    current = Decimal(item["quantity"])
    nxt = current - step
    if nxt < minimum:
        return False
    item["quantity"] = nxt
    item["total_price"] = _line_total(nxt, item["unit_price"])
    return True


def _increase_line(item: dict, headroom: Decimal, gst_rate: Decimal) -> bool:
    unit = item["unit"]
    step = QTY_STEP.get(unit, Decimal("1"))
    nxt = Decimal(item["quantity"]) + step
    max_qty = item.get("max_qty")
    if max_qty is not None and nxt > max_qty:
        return False
    trial = _line_total(nxt, item["unit_price"])
    delta = trial - item["total_price"]
    gst_delta = _money(delta * gst_rate) if item["item_type"] == BillItem.GROCERY else Decimal("0.00")
    if delta + gst_delta > headroom:
        return False
    item["quantity"] = nxt
    item["total_price"] = trial
    return True


def _fit_to_budget(
    grocery: list[dict],
    adjustments: list[dict],
    max_amount: Decimal,
    allow_grow: bool = True,
    gst_rate: Decimal = GST_RATE,
):
    target_low = _money(max_amount * Decimal("0.90"))
    _, _, _, grand = _totals(grocery, adjustments, gst_rate)

    while grand > max_amount:
        reduced = False
        grocery.sort(key=lambda i: i["total_price"], reverse=True)
        for item in grocery:
            if _reduce_line(item):
                reduced = True
                break
        if not reduced and grocery:
            grocery.pop(0)
            reduced = True
        if not reduced and adjustments:
            adjustments.sort(key=lambda i: i["total_price"], reverse=True)
            adjustments.pop(0)
            reduced = True
        if not reduced:
            break
        _refresh_totals(grocery)
        _refresh_totals(adjustments)
        _, _, _, grand = _totals(grocery, adjustments, gst_rate)

    _, _, _, grand = _totals(grocery, adjustments, gst_rate)
    safety = 0
    while allow_grow and grand < target_low and safety < 200:
        safety += 1
        headroom = max_amount - grand
        grew = False
        random.shuffle(grocery)
        for item in grocery:
            if _increase_line(item, headroom, gst_rate):
                grew = True
                break
        if not grew:
            break
        _refresh_totals(grocery)
        _, _, _, grand = _totals(grocery, adjustments, gst_rate)

    while grand > max_amount and grocery:
        if not any(_reduce_line(item) for item in grocery):
            grocery.sort(key=lambda i: i["total_price"], reverse=True)
            grocery.pop(0)
        _refresh_totals(grocery)
        _refresh_totals(adjustments)
        _, _, _, grand = _totals(grocery, adjustments, gst_rate)

    if not grocery:
        raise ValueError("max_amount is too small to generate a grocery bill.")

    return grocery, adjustments, _totals(grocery, adjustments, gst_rate)


def resolve_bill_date(
    date_mode: str,
    bill_date=None,
    date_range_start=None,
    date_range_end=None,
) -> date:
    today = date.today()

    if date_mode == Bill.DATE_FIXED:
        if not bill_date:
            raise ValueError("bill_date is required when date_mode is 'fixed'.")
        return _parse_date(bill_date)

    if date_mode == Bill.DATE_MONTHLY:
        day = _parse_date(bill_date).day if bill_date else today.day
        last_day = calendar.monthrange(today.year, today.month)[1]
        return date(today.year, today.month, min(day, last_day))

    if date_mode == Bill.DATE_RANDOM:
        start = _parse_date(date_range_start) if date_range_start else today - timedelta(days=60)
        end = _parse_date(date_range_end) if date_range_end else today
        if start > end:
            start, end = end, start
        span = (end - start).days
        return start + timedelta(days=random.randint(0, span))

    raise ValueError("date_mode must be one of: fixed, monthly, random.")


def _parse_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def make_bill_number(bill_date: date) -> str:
    return f"INV-{bill_date.strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"


def generate_bill_payload(
    *,
    shop_name: str,
    gst_number: str,
    customer_name: str,
    max_amount: Decimal,
    date_mode: str,
    bill_date=None,
    date_range_start=None,
    date_range_end=None,
    product_mode: str = "random",
    selected_products=None,
    gst_percent: Decimal = Decimal("5.00"),
    shop_address: str = "",
    customer_address: str = "",
    shop_phone: str = "",
    customer_phone: str = "",
    payment_mode: str = "cash",
) -> dict:
    if max_amount <= 0:
        raise ValueError("max_amount must be greater than 0.")

    gst_percent = Decimal(gst_percent)
    if gst_percent < 0:
        gst_percent = Decimal("0.00")
    gst_rate = _gst_fraction(gst_percent)

    resolved_date = resolve_bill_date(date_mode, bill_date, date_range_start, date_range_end)
    if product_mode == "select":
        grocery, adjustments = _lines_from_selection(selected_products or [])
        grocery, adjustments, totals = _fit_to_budget(
            grocery, adjustments, max_amount, allow_grow=False, gst_rate=gst_rate
        )
    else:
        grocery = _pick_grocery_lines(random.randint(8, 12))
        adjustments = _pick_adjustment_lines(random.randint(2, 4))
        grocery, adjustments, totals = _fit_to_budget(
            grocery, adjustments, max_amount, gst_rate=gst_rate
        )
    subtotal, gst_amount, adjustment_total, grand_total = totals

    bill_number = make_bill_number(resolved_date)
    while Bill.objects.filter(bill_number=bill_number).exists():
        bill_number = make_bill_number(resolved_date)

    bill = Bill.objects.create(
        shop_name=shop_name.strip(),
        shop_address=(shop_address or "").strip(),
        shop_phone=(shop_phone or "").strip(),
        gst_number=(gst_number or "").strip(),
        customer_name=customer_name.strip(),
        customer_address=(customer_address or "").strip(),
        customer_phone=(customer_phone or "").strip(),
        payment_mode=(payment_mode or Bill.PAY_CASH),
        bill_number=bill_number,
        date_mode=date_mode,
        bill_date=resolved_date,
        max_amount=_money(max_amount),
        gst_percent=_money(gst_percent),
        subtotal=subtotal,
        gst_amount=gst_amount,
        adjustment_total=adjustment_total,
        grand_total=grand_total,
    )

    item_rows = [
        BillItem(
            bill=bill,
            item_type=line["item_type"],
            name=line["name"],
            quantity=line["quantity"],
            unit=line["unit"],
            unit_price=line["unit_price"],
            total_price=line["total_price"],
        )
        for line in grocery + adjustments
    ]
    BillItem.objects.bulk_create(item_rows)
    return bill


def split_customer_names(customer_name: str, count: int) -> list[str]:
    names = [part.strip() for part in re.split(r"[\n,;]+", customer_name or "") if part.strip()]
    if not names:
        raise ValueError("customer_name is required.")
    if len(names) == 1:
        return names * count
    return [names[i % len(names)] for i in range(count)]


def generate_bills(
    *,
    count: int = 1,
    shop_name: str,
    gst_number: str,
    customer_name: str,
    max_amount: Decimal,
    date_mode: str,
    bill_date=None,
    date_range_start=None,
    date_range_end=None,
    product_mode: str = "random",
    selected_products=None,
    gst_percent: Decimal = Decimal("5.00"),
    shop_address: str = "",
    customer_address: str = "",
    shop_phone: str = "",
    customer_phone: str = "",
    payment_mode: str = "cash",
) -> list:
    if count < 1:
        raise ValueError("count must be at least 1.")
    names = split_customer_names(customer_name, count)
    return [
        generate_bill_payload(
            shop_name=shop_name,
            gst_number=gst_number,
            customer_name=name,
            max_amount=max_amount,
            date_mode=date_mode,
            bill_date=bill_date,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            product_mode=product_mode,
            selected_products=selected_products,
            gst_percent=gst_percent,
            shop_address=shop_address,
            customer_address=customer_address,
            shop_phone=shop_phone,
            customer_phone=customer_phone,
            payment_mode=payment_mode,
        )
        for name in names
    ]
