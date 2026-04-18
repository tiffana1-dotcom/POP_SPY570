"""Walmart product search — legacy WM_CONSUMER.ID flow and optional OAuth."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import requests

import config

LOG = logging.getLogger(__name__)

TOKEN_URL = "https://developer.api.walmart.com/api-proxy/service/affiliate/token"
OAUTH_SEARCH_URL = "https://developer.api.walmart.com/api-proxy/service/affiliate/product/v2/search"
# Prior arbitrage stack used this path + WM_CONSUMER.ID (no bearer)
LEGACY_SEARCH_URL = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2/search"


def _basic_auth_header() -> str:
    raw = f"{config.WALMART_CLIENT_ID}:{config.WALMART_CLIENT_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _get_token() -> str | None:
    if not config.WALMART_CLIENT_ID or not config.WALMART_CLIENT_SECRET:
        return None
    try:
        r = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
                "WM_PARTNER.NAME": "BeverageTrendScout",
                "WM_PARTNER.CHANNEL.TYPE": "affiliate",
                "WM_QOS.CORRELATION_ID": str(int(time.time() * 1000)),
            },
            data={"grant_type": "client_credentials"},
            timeout=25,
        )
        r.raise_for_status()
        data = r.json()
        tok = data.get("access_token")
        return str(tok) if tok else None
    except Exception as e:
        LOG.info("Walmart token failed: %s", e)
        return None


def check_walmart_gap(product_name: str) -> dict[str, Any]:
    """
    Same idea as prior code: count catalog hits; gap high when no items (0),
    med when thin, low when several matches.
    """
    q = (product_name or "").strip()
    if len(q) < 2:
        return {"walmart_count": 0, "gap": "unknown", "found": False, "note": "Empty query"}

    if not config.WALMART_KEY:
        return {
            "walmart_count": -1,
            "gap": "unknown",
            "found": False,
            "note": "WALMART_KEY not set — skipping legacy Walmart search",
        }

    headers = {
        "WM_SEC.KEY_VERSION": "1",
        "WM_CONSUMER.ID": config.WALMART_KEY,
        "Accept": "application/json",
    }
    params = {"query": q[:200], "numItems": 5}
    try:
        r = requests.get(LEGACY_SEARCH_URL, headers=headers, params=params, timeout=12)
        if not r.ok:
            return {
                "walmart_count": -1,
                "gap": "unknown",
                "found": False,
                "note": f"Walmart HTTP {r.status_code}",
            }
        data = r.json() if r.content else {}
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            items = []
        count = len(items)
        gap = "high" if count == 0 else "med" if count < 3 else "low"

        first: dict[str, Any] = items[0] if items and isinstance(items[0], dict) else {}
        price = first.get("salePrice") or first.get("price")
        if isinstance(price, dict):
            price = price.get("amount")

        return {
            "walmart_count": count,
            "gap": gap,
            "found": count > 0,
            "query": q[:120],
            "title": str(first.get("name") or "")[:200] if first else "",
            "item_id": str(first.get("itemId") or first.get("itemid") or "") if first else "",
            "price": float(price) if isinstance(price, (int, float)) else None,
            "url": str(first.get("productTrackingUrl") or first.get("productUrl") or "") if first else "",
            "note": "Legacy WM_CONSUMER.ID search",
        }
    except Exception as e:
        LOG.info("Walmart legacy search failed: %s", e)
        return {"walmart_count": -1, "gap": "unknown", "found": False, "note": str(e)[:120]}


def search_product(query: str) -> dict[str, Any]:
    """
    Prefer WALMART_KEY + legacy endpoint (matches prior project). Fall back to OAuth
    client credentials when only WALMART_CLIENT_ID / SECRET are configured.
    """
    q = (query or "").strip()
    if len(q) < 2:
        return {"found": False, "query": q, "note": "Empty query", "gap": "unknown", "walmart_count": 0}

    if config.WALMART_KEY:
        return check_walmart_gap(q)

    token = _get_token()
    if not token:
        return {
            "found": False,
            "query": q[:120],
            "walmart_count": -1,
            "gap": "unknown",
            "note": "Set WALMART_KEY (legacy) or WALMART_CLIENT_ID + WALMART_CLIENT_SECRET (OAuth)",
        }
    try:
        r = requests.get(
            OAUTH_SEARCH_URL,
            headers={
                "WM_SEC.ACCESS_TOKEN": token,
                "WM_PARTNER.NAME": "BeverageTrendScout",
                "WM_PARTNER.CHANNEL.TYPE": "affiliate",
                "WM_QOS.CORRELATION_ID": str(int(time.time() * 1000)),
                "Accept": "application/json",
            },
            params={
                "query": q[:200],
                "publisherId": config.WALMART_PUBLISHER_ID or "0",
            },
            timeout=30,
        )
        if not r.ok:
            return {
                "found": False,
                "query": q[:120],
                "walmart_count": -1,
                "gap": "unknown",
                "note": f"Walmart HTTP {r.status_code}",
            }
        data = r.json()
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            items = []
        count = len(items)
        gap = "high" if count == 0 else "med" if count < 3 else "low"
        first = items[0] if items and isinstance(items[0], dict) else {}
        price = first.get("salePrice") or first.get("price")
        if isinstance(price, dict):
            price = price.get("amount")
        return {
            "found": count > 0,
            "walmart_count": count,
            "gap": gap,
            "query": q[:120],
            "title": str(first.get("name") or "")[:200],
            "item_id": str(first.get("itemId") or first.get("itemid") or ""),
            "price": float(price) if isinstance(price, (int, float)) else None,
            "url": str(first.get("productTrackingUrl") or first.get("productUrl") or ""),
            "note": "OAuth affiliate search",
        }
    except Exception as e:
        LOG.info("Walmart OAuth search failed: %s", e)
        return {
            "found": False,
            "query": q[:120],
            "walmart_count": -1,
            "gap": "unknown",
            "note": str(e)[:120],
        }
