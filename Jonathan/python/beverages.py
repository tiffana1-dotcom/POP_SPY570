"""Beverage-only filtering and taxonomy for Amazon titles and queries."""

from __future__ import annotations

import re
from typing import Iterable

BEVERAGE_SEARCH_QUERIES: list[str] = [
    "functional beverage",
    "energy drink",
    "sparkling water",
    "protein shake ready to drink",
    "cold brew coffee bottle",
    "iced tea bottle",
    "kombucha",
    "electrolyte drink",
    "plant based milk shelf stable",
    "juice drink",
    "coca cola",
]

# Title must match at least one token/phrase to be kept
BEVERAGE_HINTS: tuple[str, ...] = (
    "beverage",
    "drink",
    "water",
    "soda",
    "juice",
    "tea",
    "coffee",
    "energy",
    "kombucha",
    "electrolyte",
    "hydration",
    "shake",
    "protein",
    "smoothie",
    "tonic",
    "seltzer",
    "sparkling",
    "cola",
    "lemonade",
    "milk",
    "oat milk",
    "almond milk",
    "coconut water",
    "sports drink",
    "rtd",
    "ready to drink",
    "shot",
    "elixir",
    "tonic",
    "brew",
    "latte",
    "espresso",
    "matcha",
)

# Non-beverage noise to drop even if a hint matches
EXCLUDE_HINTS: tuple[str, ...] = (
    "supplement capsule",
    "capsules",
    "powder only",
    "meal replacement bar",
    "protein bar",
    "snack bar",
    "candy",
    "gummy vitamin",
    "shampoo",
    "lotion",
    "cleaner",
)

BEVERAGE_TYPES_ORDER: list[str] = [
    "All types",
    "Energy & performance",
    "Coffee & cold brew",
    "Tea & botanical",
    "Water & sparkling",
    "Juice & fruit drinks",
    "Functional & wellness RTD",
    "Dairy & plant milks",
    "Other beverages",
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def is_likely_beverage_title(title: str) -> bool:
    t = _norm(title)
    if len(t) < 6:
        return False
    if any(x in t for x in EXCLUDE_HINTS):
        return False
    return any(h in t for h in BEVERAGE_HINTS)


def classify_beverage_type(title: str) -> str:
    t = _norm(title)
    if any(x in t for x in ("energy", "pre workout", "preworkout", "electrolyte", "sports drink")):
        return "Energy & performance"
    if any(x in t for x in ("coffee", "cold brew", "latte", "espresso", "mocha")):
        return "Coffee & cold brew"
    if any(x in t for x in ("tea", "matcha", "kombucha", "botanical", "yerba")):
        return "Tea & botanical"
    if any(x in t for x in ("water", "seltzer", "sparkling", "tonic", "soda", "cola")):
        return "Water & sparkling"
    if any(x in t for x in ("juice", "lemonade", "fruit drink", "smoothie")):
        return "Juice & fruit drinks"
    if any(
        x in t
        for x in (
            "functional",
            "wellness",
            "vitamin",
            "adaptogen",
            "probiotic drink",
            "immunity",
        )
    ):
        return "Functional & wellness RTD"
    if any(x in t for x in ("milk", "oat", "almond", "soy", "coconut milk", "dairy")):
        return "Dairy & plant milks"
    return "Other beverages"


def dedupe_asins(rows: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        asin = (row.get("asin") or "").strip().upper()
        if not asin or asin in seen:
            continue
        seen.add(asin)
        out.append(row)
    return out
