"""Live unit prices for the grocery catalogue.

Google Shopping / Google Search are tried first. When Google serves a
bot-check page, official all-India retail prices from the Department of
Consumer Affairs (the same figures Google often shows for staples) and
public web snippets are used instead.
"""

from __future__ import annotations

import json
import random
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from html import unescape
from pathlib import Path
from typing import Callable

from .constants import ADJUSTMENT_ITEMS, GROCERY_ITEMS

PRICE_FILE = Path(__file__).resolve().parent / "data" / "live_prices.json"
IST = timezone(timedelta(hours=5, minutes=30))
TWO_PLACES = Decimal("0.01")

GOOGLE_SHOP = "https://www.google.com/search?tbm=shop&hl=en&gl=in&num=20&q={query}"
GOOGLE_WEB = "https://www.google.com/search?hl=en&gl=in&gbv=1&num=10&q={query}"
DDG_HTML = "https://html.duckduckgo.com/html/?q={query}"
DOCA_URL = "https://fcainfoweb.nic.in/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}

RUPEE_RE = re.compile(
    r"(?:₹|&\#8377;|&amp;\#8377;|Rs\.?\s*|INR\s*)\s*"
    r"([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)

# Official DoCA retail names -> (catalogue name, multiplier to our unit).
# Spice pack sizes follow DoCA report units (50g / 100g / 250g).
DOCA_TO_CATALOG = {
    "Rice": [("Sona Masuri Rice", Decimal("1"))],
    "Atta (Wheat)": [("Wheat Atta", Decimal("1"))],
    "Tur/Arhar Dal": [("Toor Dal", Decimal("1"))],
    "Moong Dal": [("Moong Dal", Decimal("1"))],
    "Gram Dal": [("Chana Dal", Decimal("1"))],
    "Urad Dal": [("Urad Dal", Decimal("1"))],
    "Masoor Dal": [("Masoor Dal", Decimal("1"))],
    "Sunflower Oil (Packed)": [("Sunflower Oil", Decimal("1"))],
    "Mustard Oil (Packed)": [("Mustard Oil", Decimal("1"))],
    "Groundnut Oil (Packed)": [("Groundnut Oil", Decimal("1"))],
    "Sugar": [("Sugar", Decimal("1"))],
    "Salt Pack (Iodised)": [("Iodized Salt", Decimal("1"))],
    "Tea Loose": [("Tea Leaf", Decimal("1"))],
    "Milk @": [("Toned Milk", Decimal("1"))],
    "Onion": [("Onion", Decimal("1"))],
    "Potato": [("Potato", Decimal("1"))],
    "Tomato": [("Tomato", Decimal("1"))],
    "Turmeric (powder)": [("Turmeric Powder", Decimal("20"))],  # 50g pack
    "Red Chillies (whole)": [("Red Chilli Powder", Decimal("10"))],  # 100g pack
    "Coriander (whole)": [("Coriander Powder", Decimal("4"))],  # 250g pack
    "Banana": [("Banana", Decimal("0.125"))],  # kg -> piece
}

SEARCH_QUERIES = {
    "Basmati Rice": "basmati rice 1kg price India",
    "Sona Masuri Rice": "sona masuri rice 1kg price India",
    "Wheat Atta": "wheat atta 1kg price India",
    "Toor Dal": "toor dal 1kg price India",
    "Moong Dal": "moong dal 1kg price India",
    "Chana Dal": "chana dal 1kg price India",
    "Urad Dal": "urad dal 1kg price India",
    "Masoor Dal": "masoor dal 1kg price India",
    "Sunflower Oil": "sunflower oil 1 litre price India",
    "Mustard Oil": "mustard oil 1 litre price India",
    "Groundnut Oil": "groundnut oil 1 litre price India",
    "Sugar": "sugar 1kg price India",
    "Iodized Salt": "iodized salt 1kg price India",
    "Turmeric Powder": "turmeric powder 100g price India",
    "Red Chilli Powder": "red chilli powder 100g price India",
    "Coriander Powder": "coriander powder 100g price India",
    "Garam Masala": "garam masala 100g price India",
    "Tea Leaf": "tea powder 1kg price India",
    "Instant Coffee": "instant coffee 100g price India",
    "Toned Milk": "toned milk 1 litre price India",
    "Bread Loaf": "bread loaf price India",
    "Onion": "onion price per kg India today",
    "Potato": "potato price per kg India today",
    "Tomato": "tomato price per kg India today",
    "Green Chilli": "green chilli price per kg India",
    "Banana": "banana price per piece India",
    "Apple": "apple price per kg India",
    "Marie Biscuits": "marie biscuit pack price India",
    "Bath Soap": "bath soap price India",
    "Detergent Powder": "detergent powder 1kg price India",
    "Chocolate Eclair": "eclairs chocolate candy price India",
    "Paan": "paan price India",
    "Chewing Gum": "chewing gum price India",
    "Candy": "candy price India",
    "Small Biscuit Packet": "small biscuit packet price India",
    "Toffee": "toffee price India",
    "Mentos": "mentos candy price India",
    "Lollipop": "lollipop price India",
    "Mouth Freshener": "mouth freshener sachet price India",
    "Mini Chocolate Bar": "mini chocolate bar price India",
}

# Convert extracted listing price into per-catalogue-unit price.
PACK_SCALE = {
    "Turmeric Powder": Decimal("10"),  # 100g listing -> /kg
    "Red Chilli Powder": Decimal("10"),
    "Coriander Powder": Decimal("10"),
    "Garam Masala": Decimal("10"),
    "Instant Coffee": Decimal("10"),
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _ssl_context() -> ssl.SSLContext:
    try:
        return ssl.create_default_context()
    except ssl.SSLError:
        return ssl._create_unverified_context()


def _fetch(url: str, timeout: int = 5) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    errors: list[Exception] = []
    for context in (_ssl_context(), ssl._create_unverified_context()):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                return resp.read().decode("utf-8", "replace")
        except (ssl.SSLError, urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(exc)
    raise errors[-1]


def _is_blocked(html: str) -> bool:
    text = html.lower()
    return any(
        marker in text
        for marker in (
            "unusual traffic",
            "enablejs",
            "sg_rel",
            "detected unusual",
            "captcha",
            "before you continue",
        )
    ) or ("<title>google search</title>" in text and "result" not in text)


def _parse_amounts(html: str) -> list[Decimal]:
    values: list[Decimal] = []
    for raw in RUPEE_RE.findall(unescape(html)):
        try:
            values.append(Decimal(raw.replace(",", "")))
        except (InvalidOperation, ValueError):
            continue
    return values


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _range_for(name: str, unit: str, fallback: Decimal) -> tuple[Decimal, Decimal]:
    low = fallback * Decimal("0.35")
    high = fallback * Decimal("3.5")
    lowered = name.lower()
    if unit == "pcs":
        if "banana" in lowered:
            return Decimal("3"), Decimal("15")
        if any(word in lowered for word in ("candy", "toffee", "lollipop", "mentos", "eclair")):
            return Decimal("0.50"), Decimal("15")
        if "paan" in lowered:
            return Decimal("8"), Decimal("40")
        return Decimal("1"), Decimal("120")
    if unit == "ltr":
        if "milk" in lowered:
            return Decimal("40"), Decimal("90")
        return Decimal("90"), Decimal("320")
    if "coffee" in lowered:
        return Decimal("1500"), Decimal("8000")
    if any(word in lowered for word in ("masala", "turmeric", "chilli", "coriander")):
        return Decimal("80"), Decimal("2000")
    if any(word in lowered for word in ("dal", "rice", "atta")):
        return Decimal("30"), Decimal("250")
    if any(word in lowered for word in ("onion", "potato", "tomato", "salt", "sugar")):
        return Decimal("10"), Decimal("120")
    return max(Decimal("1"), low), max(high, fallback * Decimal("2"))


def search_query(name: str) -> str:
    return SEARCH_QUERIES.get(name, f"{name} price India")


def _google_price(name: str, unit: str, fallback: Decimal) -> tuple[Decimal | None, str, bool]:
    """Return (price, source, google_blocked)."""
    query = urllib.parse.quote_plus(search_query(name))
    low, high = _range_for(name, unit, fallback)
    scale = PACK_SCALE.get(name, Decimal("1"))
    blocked = False
    for label, template in (("google-shopping", GOOGLE_SHOP), ("google-search", GOOGLE_WEB)):
        try:
            html = _fetch(template.format(query=query))
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        if _is_blocked(html):
            blocked = True
            continue
        amounts = [value * scale for value in _parse_amounts(html)]
        usable = [value for value in amounts if low <= value <= high]
        picked = _median(usable)
        if picked is not None:
            return _money(picked), label, False
    return None, "", blocked


def _web_price(name: str, unit: str, fallback: Decimal) -> tuple[Decimal | None, str]:
    query = urllib.parse.quote_plus(search_query(name))
    low, high = _range_for(name, unit, fallback)
    scale = PACK_SCALE.get(name, Decimal("1"))
    try:
        html = _fetch(DDG_HTML.format(query=query))
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, ""
    amounts = [value * scale for value in _parse_amounts(html)]
    usable = [value for value in amounts if low <= value <= high]
    picked = _median(usable)
    if picked is None:
        return None, ""
    return _money(picked), "web"


def fetch_doca_prices() -> dict[str, Decimal]:
    html = _fetch(DOCA_URL, timeout=25)
    mapped: dict[str, Decimal] = {}
    for table in re.findall(
        r'id="GridViewRetailGroup[A-E]".*?</table>', html, flags=re.IGNORECASE | re.DOTALL
    ):
        rows = re.findall(
            r'lblCommName">\s*(.*?)\s*</span>.*?lblPrices">\s*([0-9]+(?:\.[0-9]+)?)\s*</span>',
            table,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for raw_name, raw_price in rows:
            name = unescape(re.sub(r"\s+", " ", raw_name)).strip()
            price = Decimal(raw_price)
            for catalog_name, multiplier in DOCA_TO_CATALOG.get(name, []):
                mapped[catalog_name] = _money(price * multiplier)
    return mapped


def load_live_prices() -> dict:
    if not PRICE_FILE.exists():
        return {"updated_at": None, "items": {}}
    try:
        return json.loads(PRICE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"updated_at": None, "items": {}}


def save_live_prices(payload: dict) -> None:
    PRICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRICE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def apply_live_prices(items: list[dict]) -> list[dict]:
    cache = load_live_prices().get("items") or {}
    updated = []
    for item in items:
        row = dict(item)
        live = cache.get(row["name"])
        if live and live.get("unit_price"):
            row["unit_price"] = Decimal(str(live["unit_price"]))
            row["price_source"] = live.get("source")
        updated.append(row)
    return updated


def grocery_catalog() -> list[dict]:
    return apply_live_prices(GROCERY_ITEMS)


def adjustment_catalog() -> list[dict]:
    return apply_live_prices(ADJUSTMENT_ITEMS)


def refresh_live_prices(progress: Callable[[str], None] | None = None, time_budget: float = 20.0) -> dict:
    def log(message: str) -> None:
        if progress:
            progress(message)

    cache = load_live_prices()
    items = cache.get("items") or {}
    catalog = list(GROCERY_ITEMS) + list(ADJUSTMENT_ITEMS)

    doca: dict[str, Decimal] = {}
    try:
        log("Fetching official retail prices…")
        doca = fetch_doca_prices()
        log(f"Official retail prices loaded for {len(doca)} staples.")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        log(f"Official retail feed unavailable: {exc}")

    updated = 0
    google_ok = True
    start = time.monotonic()
    for sku in catalog:
        if google_ok and time.monotonic() - start > time_budget:
            google_ok = False
            log("Time budget reached; using official retail and web prices for the rest.")
        name = sku["name"]
        fallback = Decimal(sku["unit_price"])
        unit = sku["unit"]
        price, source = None, ""
        if google_ok:
            price, source, blocked = _google_price(name, unit, fallback)
            if blocked and price is None:
                google_ok = False
                log("Google returned a bot-check page; using official retail and web prices.")
            elif price is not None:
                time.sleep(0.4)
        if price is None and name in doca:
            price, source = doca[name], "official-retail"
        if price is None:
            price, source = _web_price(name, unit, fallback)
            time.sleep(0.25 + random.random() * 0.2)
        if price is None:
            log(f"Kept previous price for {name}")
            continue
        items[name] = {
            "unit_price": str(price),
            "source": source,
            "query": search_query(name),
        }
        updated += 1
        log(f"{name}: Rs {price} ({source})")

    payload = {
        "updated_at": datetime.now(tz=IST).isoformat(timespec="seconds"),
        "timezone": "Asia/Kolkata",
        "items": items,
        "updated_count": updated,
    }
    save_live_prices(payload)
    return payload
