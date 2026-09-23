from __future__ import annotations

import calendar
import random
import re
import secrets
from copy import deepcopy
from datetime import date, datetime, time, timedelta
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


def _sku_line(sku: dict, item_type: str, quantity: Decimal | None = None) -> dict:
    if quantity is None:
        if item_type == BillItem.GROCERY:
            options = sku.get("qty_options") or ["1"]
            quantity = Decimal(random.choice(options))
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
        options = sku.get("qty_options") or [str(quantity)]
        line["max_qty"] = max(Decimal(max(options)), quantity)
    return line


def _pick_grocery_lines(count: int, pool: list[dict] | None = None) -> list[dict]:
    grocery = pool if pool is not None else grocery_catalog()
    if not grocery:
        return []
    sample = deepcopy(random.sample(grocery, k=min(count, len(grocery))))
    return [_sku_line(sku, BillItem.GROCERY) for sku in sample]


def _pick_adjustment_lines(count: int, pool: list[dict] | None = None) -> list[dict]:
    adjustments = pool if pool is not None else adjustment_catalog()
    if not adjustments or count <= 0:
        return []
    sample = deepcopy(random.sample(adjustments, k=min(count, len(adjustments))))
    return [_sku_line(sku, BillItem.ADJUSTMENT) for sku in sample]


def _deal_sku_batches(catalog: list[dict], bill_count: int, min_k: int, max_k: int) -> list[list[dict]]:
    if bill_count < 1:
        return []
    if not catalog:
        return [[] for _ in range(bill_count)]
    deck = deepcopy(catalog)
    random.shuffle(deck)
    n = len(deck)
    batches: list[list[dict]] = []
    cursor = 0
    seen: set[tuple[str, ...]] = set()
    for _ in range(bill_count):
        low = min(min_k, n)
        high = min(max_k, n)
        if high < low:
            low = high
        k = random.randint(low, high) if high > 0 else 0
        if k <= 0:
            batches.append([])
            continue
        if n > 1 and bill_count > 1 and k == n and n > 2:
            k = max(1, n - 1)
        batch = [deck[(cursor + i) % n] for i in range(k)]
        fingerprint = tuple(sorted(sku["name"] for sku in batch))
        attempts = 0
        while fingerprint in seen and attempts < 20 and n > 1:
            cursor = (cursor + 1) % n
            k = random.randint(low, high)
            if n > 1 and bill_count > 1 and k == n and n > 2:
                k = max(1, n - 1)
            batch = [deck[(cursor + i) % n] for i in range(k)]
            fingerprint = tuple(sorted(sku["name"] for sku in batch))
            attempts += 1
        seen.add(fingerprint)
        cursor = (cursor + max(k, 1)) % n
        batches.append(batch)
    return batches


def _lines_from_skus(skus: list[dict], item_type: str) -> list[dict]:
    return [_sku_line(sku, item_type) for sku in deepcopy(skus)]


def _catalog_lookup() -> dict[str, tuple[str, dict]]:
    lookup = {sku["name"]: (BillItem.GROCERY, sku) for sku in grocery_catalog()}
    lookup.update({sku["name"]: (BillItem.ADJUSTMENT, sku) for sku in adjustment_catalog()})
    return lookup


def _lines_from_selection(selected_products: list[dict], randomize: bool = False) -> tuple[list[dict], list[dict]]:
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
        if randomize or raw_qty is None or str(raw_qty) == "":
            quantity = None
        else:
            quantity = Decimal(str(raw_qty))
            if quantity <= 0:
                raise ValueError(f"Quantity for {name} must be greater than 0.")

        line = _sku_line(sku, item_type, quantity)
        if item_type == BillItem.GROCERY:
            grocery.append(line)
        else:
            adjustments.append(line)
        seen.add(name)

    if not grocery:
        raise ValueError("Select at least one grocery product.")
    return grocery, adjustments


def _selection_pools(selected_products: list[dict]) -> tuple[list[dict], list[dict]]:
    lookup = _catalog_lookup()
    grocery: list[dict] = []
    adjustments: list[dict] = []
    seen: set[str] = set()
    for entry in selected_products or []:
        name = str(entry.get("name") or "").strip()
        if not name or name in seen:
            continue
        if name not in lookup:
            raise ValueError(f"Unknown product: {name}")
        item_type, sku = lookup[name]
        if item_type == BillItem.GROCERY:
            grocery.append(sku)
        else:
            adjustments.append(sku)
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
        if bill_date:
            return _parse_date(bill_date)
        if date_range_start:
            return _parse_date(date_range_start)
        day = today.day
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


def monthly_bill_dates(date_range_start, date_range_end) -> list[date]:
    if not date_range_start or not date_range_end:
        raise ValueError("Start range and end range are required when date mode is monthly.")
    start = _parse_date(date_range_start)
    end = _parse_date(date_range_end)
    if start > end:
        start, end = end, start
    dates: list[date] = []
    year, month = start.year, start.month
    day = start.day
    while (year, month) <= (end.year, end.month):
        last_day = calendar.monthrange(year, month)[1]
        bill_day = date(year, month, min(day, last_day))
        if bill_day < start:
            bill_day = start
        if bill_day > end:
            bill_day = end
        dates.append(bill_day)
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    if len(dates) > 36:
        raise ValueError("Monthly range cannot exceed 36 months.")
    return dates


def _parse_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def make_bill_number(_bill_date: date) -> str:
    # Match the sample grocery invoices (short numeric invoice nos).
    for width in (4, 5, 6):
        low = 10 ** (width - 1)
        high = (10 ** width) - 1
        for _ in range(40):
            number = f"{random.randint(low, high)}"
            if not Bill.objects.filter(bill_number=number).exists():
                return number
    return f"{secrets.randbelow(900000) + 100000}"


def make_bill_time(used: set[str] | None = None) -> time:
    """Random shop hours time; unique within a generate batch when possible."""
    used = used if used is not None else set()
    for _ in range(80):
        hour = random.randint(9, 20)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        candidate = time(hour, minute, second)
        key = candidate.strftime("%H:%M:%S")
        if key not in used:
            used.add(key)
            return candidate
    return time(random.randint(9, 20), random.randint(0, 59), random.randint(0, 59))


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
    receipt_template: str = Bill.TEMPLATE_INVOICE,
    used_times: set[str] | None = None,
    grocery_lines=None,
    adjustment_lines=None,
    allow_grow: bool | None = None,
) -> dict:
    if max_amount <= 0:
        raise ValueError("max_amount must be greater than 0.")

    gst_percent = Decimal(gst_percent)
    if gst_percent < 0:
        gst_percent = Decimal("0.00")
    gst_rate = _gst_fraction(gst_percent)

    resolved_date = resolve_bill_date(date_mode, bill_date, date_range_start, date_range_end)
    if grocery_lines is not None:
        grocery = deepcopy(grocery_lines)
        adjustments = deepcopy(adjustment_lines or [])
        grow = product_mode != "select" if allow_grow is None else allow_grow
        grocery, adjustments, totals = _fit_to_budget(
            grocery, adjustments, max_amount, allow_grow=grow, gst_rate=gst_rate
        )
    elif product_mode == "select":
        grocery, adjustments = _lines_from_selection(selected_products or [])
        grocery, adjustments, totals = _fit_to_budget(
            grocery, adjustments, max_amount, allow_grow=False, gst_rate=gst_rate
        )
    else:
        grocery = _pick_grocery_lines(random.randint(6, 11))
        adjustments = _pick_adjustment_lines(random.randint(1, 4))
        grocery, adjustments, totals = _fit_to_budget(
            grocery, adjustments, max_amount, gst_rate=gst_rate
        )
    subtotal, gst_amount, adjustment_total, grand_total = totals

    bill_number = make_bill_number(resolved_date)
    while Bill.objects.filter(bill_number=bill_number).exists():
        bill_number = make_bill_number(resolved_date)

    template = receipt_template or Bill.TEMPLATE_INVOICE
    if template not in {c[0] for c in Bill.TEMPLATE_CHOICES}:
        template = Bill.TEMPLATE_INVOICE

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
        bill_time=make_bill_time(used_times),
        receipt_template=template,
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


def _bill_line_batches(count: int, product_mode: str, selected_products) -> list[tuple[list[dict], list[dict]]]:
    if count < 1:
        return []
    if product_mode == "select":
        grocery_pool, adj_pool = _selection_pools(selected_products or [])
        if count == 1:
            grocery, adjustments = _lines_from_selection(selected_products or [])
            return [(grocery, adjustments)]
        grocery_batches = _deal_sku_batches(grocery_pool, count, min_k=max(1, min(4, len(grocery_pool))), max_k=len(grocery_pool))
        adj_batches = _deal_sku_batches(adj_pool, count, min_k=0, max_k=len(adj_pool)) if adj_pool else [[] for _ in range(count)]
        return [
            (_lines_from_skus(grocery, BillItem.GROCERY), _lines_from_skus(adjustments, BillItem.ADJUSTMENT))
            for grocery, adjustments in zip(grocery_batches, adj_batches)
        ]

    grocery_batches = _deal_sku_batches(grocery_catalog(), count, min_k=6, max_k=11)
    adj_batches = _deal_sku_batches(adjustment_catalog(), count, min_k=1, max_k=4)
    return [
        (_lines_from_skus(grocery, BillItem.GROCERY), _lines_from_skus(adjustments, BillItem.ADJUSTMENT))
        for grocery, adjustments in zip(grocery_batches, adj_batches)
    ]


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
    receipt_template: str = Bill.TEMPLATE_INVOICE,
) -> list:
    if date_mode == Bill.DATE_MONTHLY:
        month_dates = monthly_bill_dates(date_range_start, date_range_end)
        names = split_customer_names(customer_name, len(month_dates))
        used_times: set[str] = set()
        batches = _bill_line_batches(len(month_dates), product_mode, selected_products)
        return [
            generate_bill_payload(
                shop_name=shop_name,
                gst_number=gst_number,
                customer_name=name,
                max_amount=max_amount,
                date_mode=date_mode,
                bill_date=month_date,
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
                receipt_template=receipt_template,
                used_times=used_times,
                grocery_lines=grocery,
                adjustment_lines=adjustments,
                allow_grow=product_mode != "select" or len(month_dates) > 1,
            )
            for name, month_date, (grocery, adjustments) in zip(names, month_dates, batches)
        ]

    if count < 1:
        raise ValueError("count must be at least 1.")
    names = split_customer_names(customer_name, count)
    used_times: set[str] = set()
    batches = _bill_line_batches(count, product_mode, selected_products)
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
            receipt_template=receipt_template,
                used_times=used_times,
                grocery_lines=grocery,
                adjustment_lines=adjustments,
                allow_grow=product_mode != "select" or count > 1,
            )
        for name, (grocery, adjustments) in zip(names, batches)
    ]
