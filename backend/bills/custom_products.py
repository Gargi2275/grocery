"""User-added and user-edited grocery products with a price per kg / g / ltr / ml / pcs."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from .constants import ADJUSTMENT_ITEMS, GROCERY_ITEMS

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


def _load_raw() -> dict:
    if not CUSTOM_FILE.exists():
        return {"items": [], "hidden": []}
    try:
        payload = json.loads(CUSTOM_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"items": [], "hidden": []}
    if isinstance(payload, list):
        return {"items": payload, "hidden": []}
    if not isinstance(payload, dict):
        return {"items": [], "hidden": []}
    items = payload.get("items")
    hidden = payload.get("hidden")
    return {
        "items": items if isinstance(items, list) else [],
        "hidden": hidden if isinstance(hidden, list) else [],
    }


def load_custom_records() -> list[dict]:
    raw = _load_raw()
    return [row for row in raw["items"] if isinstance(row, dict)]


def load_hidden_names() -> list[str]:
    raw = _load_raw()
    return [str(name).strip().lower() for name in raw["hidden"] if str(name).strip()]


def save_custom_data(items: list[dict], hidden: list[str] | None = None) -> None:
    if hidden is None:
        hidden = load_hidden_names()
    CUSTOM_FILE.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    deduped_hidden = []
    for h in hidden:
        clean = str(h).strip().lower()
        if clean and clean not in seen:
            seen.add(clean)
            deduped_hidden.append(clean)

    payload = {
        "items": items,
        "hidden": deduped_hidden,
    }
    CUSTOM_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_custom_records(items: list[dict]) -> None:
    save_custom_data(items, load_hidden_names())


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
    hidden = set(load_hidden_names())
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
        if row["name"].lower() in hidden:
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


def _is_builtin_name(name_lower: str) -> bool:
    builtin_names = {item["name"].lower() for item in GROCERY_ITEMS} | {
        item["name"].lower() for item in ADJUSTMENT_ITEMS
    }
    return name_lower in builtin_names


def add_custom_product(name: str, unit: str, unit_price, item_type: str = "grocery") -> dict:
    row = _normalize(name, unit, unit_price, item_type)
    name_clean = row["name"].lower()
    items = load_custom_records()
    hidden = [h for h in load_hidden_names() if h != name_clean]
    items = [item for item in items if str(item.get("name") or "").strip().lower() != name_clean]
    items.append(
        {
            "name": row["name"],
            "unit": row["unit"],
            "unit_price": row["unit_price"],
            "item_type": row["item_type"],
        }
    )
    items.sort(key=lambda item: str(item.get("name") or "").lower())
    save_custom_data(items, hidden)
    return row


def update_custom_product(
    original_name: str,
    name: str,
    unit: str,
    unit_price,
    item_type: str = "grocery",
) -> dict:
    row = _normalize(name, unit, unit_price, item_type)
    orig_clean = " ".join(str(original_name or "").split()).lower()
    new_clean = row["name"].lower()

    items = load_custom_records()
    hidden = [h for h in load_hidden_names() if h not in {orig_clean, new_clean}]

    # Filter out both old and new names from custom items
    items = [
        item
        for item in items
        if str(item.get("name") or "").strip().lower() not in {orig_clean, new_clean}
    ]

    # If original name was a built-in SKU and the user renamed it, hide the old built-in name
    if orig_clean and orig_clean != new_clean and _is_builtin_name(orig_clean):
        hidden.append(orig_clean)

    items.append(
        {
            "name": row["name"],
            "unit": row["unit"],
            "unit_price": row["unit_price"],
            "item_type": row["item_type"],
        }
    )
    items.sort(key=lambda item: str(item.get("name") or "").lower())
    save_custom_data(items, hidden)
    return row


def delete_custom_product(name: str) -> bool:
    needle = " ".join(str(name or "").split()).lower()
    if not needle:
        return False
    items = load_custom_records()
    hidden = load_hidden_names()
    orig_item_count = len(items)
    kept_items = [item for item in items if str(item.get("name") or "").strip().lower() != needle]
    
    # If it was a built-in item or in catalog, add to hidden
    is_builtin = _is_builtin_name(needle)
    if is_builtin and needle not in hidden:
        hidden.append(needle)

    if len(kept_items) == orig_item_count and not is_builtin:
        return False

    save_custom_data(kept_items, hidden)
    return True


def reset_catalog_defaults() -> None:
    save_custom_data([], [])
