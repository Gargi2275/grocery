"""User-added grocery products with a price per kg / g / ltr / ml / pcs."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

UNITS = ("kg", "g", "ltr", "ml", "pcs")

QTY_OPTIONS = {
    "kg": ["0.25", "0.5", "1", "2", "5"],
    "g": ["50", "100", "200", "250", "500"],
    "ltr": ["0.25", "0.5", "1", "2"],
    "ml": ["100", "200", "500", "1000"],
    "pcs": ["1", "2", "3", "6"],
}

CUSTOM_FILE = Path(__file__).resolve().parent / "data" / "custom_products.json"
TWO_PLACES = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def load_custom_records() -> list[dict]:
    if not CUSTOM_FILE.exists():
        return []
    try:
        payload = json.loads(CUSTOM_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []
    return [row for row in items if isinstance(row, dict)]


def save_custom_records(items: list[dict]) -> None:
    CUSTOM_FILE.parent.mkdir(parents=True, exist_ok=True)
    CUSTOM_FILE.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")


def _normalize(name: str, unit: str, unit_price, item_type: str = "grocery") -> dict:
    clean_name = " ".join(str(name or "").split())
    if not clean_name:
        raise ValueError("Product name is required.")
    clean_unit = str(unit or "").strip().lower()
    if clean_unit in {"liter", "litre", "liters", "litres", "lt"}:
        clean_unit = "ltr"
    if clean_unit in {"gram", "grams", "gm"}:
        clean_unit = "g"
    if clean_unit in {"kgs", "kilo", "kilos"}:
        clean_unit = "kg"
    if clean_unit in {"piece", "pieces", "pc", "nos"}:
        clean_unit = "pcs"
    if clean_unit not in UNITS:
        raise ValueError("Unit must be kg, g, ltr, ml, or pcs.")
    try:
        price = _money(Decimal(str(unit_price)))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Enter a valid price.") from exc
    if price <= 0:
        raise ValueError("Price must be greater than 0.")
    kind = str(item_type or "grocery").strip().lower()
    if kind not in {"grocery", "adjustment"}:
        kind = "grocery"
    return {
        "name": clean_name,
        "unit": clean_unit,
        "unit_price": str(price),
        "item_type": kind,
        "qty_options": list(QTY_OPTIONS[clean_unit]),
        "custom": True,
    }


def custom_skus(item_type: str) -> list[dict]:
    rows = []
    for record in load_custom_records():
        try:
            row = _normalize(
                record.get("name"),
                record.get("unit"),
                record.get("unit_price"),
                record.get("item_type") or "grocery",
            )
        except ValueError:
            continue
        if row["item_type"] != item_type:
            continue
        rows.append(
            {
                "name": row["name"],
                "unit": row["unit"],
                "unit_price": Decimal(row["unit_price"]),
                "qty_options": row["qty_options"],
                "custom": True,
            }
        )
    return rows


def add_custom_product(name: str, unit: str, unit_price, item_type: str = "grocery") -> dict:
    row = _normalize(name, unit, unit_price, item_type)
    items = load_custom_records()
    items = [item for item in items if str(item.get("name") or "").strip().lower() != row["name"].lower()]
    items.append(
        {
            "name": row["name"],
            "unit": row["unit"],
            "unit_price": row["unit_price"],
            "item_type": row["item_type"],
        }
    )
    items.sort(key=lambda item: str(item.get("name") or "").lower())
    save_custom_records(items)
    return row


def delete_custom_product(name: str) -> bool:
    needle = " ".join(str(name or "").split()).lower()
    if not needle:
        return False
    items = load_custom_records()
    kept = [item for item in items if str(item.get("name") or "").strip().lower() != needle]
    if len(kept) == len(items):
        return False
    save_custom_records(kept)
    return True
