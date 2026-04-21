"""Rainforest API — Amazon search + product (beverage-focused)."""

from __future__ import annotations

import logging
from typing import Any

import requests

import config

LOG = logging.getLogger(__name__)
BASE = "https://api.rainforestapi.com/request"


def _get(url: str, params: dict[str, str]) -> dict[str, Any]:
    r = requests.get(url, params=params, timeout=45)
    r.raise_for_status()
    return r.json()


def search(term: str, page: int = 1) -> list[dict[str, Any]]:
    if not config.RAINFOREST_API_KEY:
        raise RuntimeError("RAINFOREST_API_KEY is not set")
    data = _get(
        BASE,
        {
            "api_key": config.RAINFOREST_API_KEY,
            "type": "search",
            "amazon_domain": config.AMAZON_DOMAIN,
            "search_term": term,
            "page": str(max(1, page)),
        },
    )
    return list(data.get("search_results") or [])


def product(asin: str) -> dict[str, Any] | None:
    if not config.RAINFOREST_API_KEY:
        raise RuntimeError("RAINFOREST_API_KEY is not set")
    data = _get(
        BASE,
        {
            "api_key": config.RAINFOREST_API_KEY,
            "type": "product",
            "amazon_domain": config.AMAZON_DOMAIN,
            "asin": asin.strip().upper(),
        },
    )
    p = data.get("product")
    return p if isinstance(p, dict) else None


def pick_image(hit_or_product: dict[str, Any]) -> str:
    def first_url(x: Any) -> str:
        if isinstance(x, str) and x.startswith("http"):
            return x
        if isinstance(x, dict) and isinstance(x.get("link"), str):
            u = x["link"]
            return u if u.startswith("http") else ""
        return ""

    for key in ("image", "thumbnail", "main_image"):
        v = hit_or_product.get(key)
        u = first_url(v)
        if u:
            return u
        if isinstance(v, dict):
            u = first_url(v.get("link"))
            if u:
                return u
    imgs = hit_or_product.get("images")
    if isinstance(imgs, list):
        for im in imgs:
            u = first_url(im)
            if u:
                return u
            if isinstance(im, dict):
                u = first_url(im.get("link"))
                if u:
                    return u
    return ""


def best_bsr_rank(product_payload: dict[str, Any]) -> int | None:
    ranks = product_payload.get("bestsellers_rank")
    if not isinstance(ranks, list) or not ranks:
        return None
    best: int | None = None
    for entry in ranks:
        if not isinstance(entry, dict):
            continue
        rk = entry.get("rank")
        if isinstance(rk, int):
            best = rk if best is None else min(best, rk)
    return best


def parse_search_row(hit: dict[str, Any]) -> dict[str, Any] | None:
    asin = (hit.get("asin") or "").strip().upper()
    if not asin or hit.get("is_sponsored"):
        return None
    title = str(hit.get("title") or "").strip()
    return {"asin": asin, "title": title, "image": pick_image(hit)}


def parse_product_row(p: dict[str, Any]) -> dict[str, Any]:
    asin = str(p.get("asin") or "").strip().upper()
    title = str(p.get("title") or "").strip()
    buybox = p.get("buybox_winner") if isinstance(p.get("buybox_winner"), dict) else {}
    price_val = None
    if isinstance(buybox, dict):
        pv = buybox.get("price")
        if isinstance(pv, dict) and isinstance(pv.get("value"), (int, float)):
            price_val = float(pv["value"])
    rating = p.get("rating")
    ratings_total = p.get("ratings_total")
    return {
        "asin": asin,
        "title": title,
        "image": pick_image(p),
        "price": price_val,
        "rating": float(rating) if isinstance(rating, (int, float)) else None,
        "reviews": int(ratings_total) if isinstance(ratings_total, int) else 0,
        "bsr": best_bsr_rank(p),
        "url": f"https://www.{config.AMAZON_DOMAIN}/dp/{asin}",
    }
