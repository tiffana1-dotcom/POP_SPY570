"""End-to-end beverage pipeline: Rainforest + Trends + Walmart + Reddit."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import beverages
import config
import rainforest_client as rf
import reddit_client
import scoring
import trends_client
import walmart_client

LOG = logging.getLogger(__name__)


def _short_kw(title: str) -> str:
    t = title.replace("Pack of", "").replace("Count", "")
    parts = [p for p in t.split() if len(p) > 2][:8]
    return " ".join(parts)[:80]


def build_feed() -> dict[str, Any]:
    source_status: dict[str, str] = {
        "rainforest": "skipped",
        "google_trends": "pending",
        "walmart": "pending",
        "reddit": "pending",
    }
    rows: list[dict[str, Any]] = []

    if not config.RAINFOREST_API_KEY:
        raise RuntimeError(
            "RAINFOREST_API_KEY is required to refresh live Amazon beverage data."
        )

    seen: set[str] = set()
    for q in beverages.BEVERAGE_SEARCH_QUERIES:
        for page in range(1, max(1, config.RAINFOREST_SEARCH_PAGES) + 1):
            try:
                hits = rf.search(q, page=page)
            except Exception as e:
                LOG.warning("Rainforest search %r page %s: %s", q, page, e)
                source_status["rainforest"] = "partial_error"
                continue
            source_status["rainforest"] = "ok"
            for hit in hits:
                parsed = rf.parse_search_row(hit if isinstance(hit, dict) else {})
                if not parsed:
                    continue
                asin = parsed["asin"]
                if asin in seen:
                    continue
                if not beverages.is_likely_beverage_title(parsed["title"]):
                    continue
                seen.add(asin)
                rows.append(parsed)
                if len(rows) >= config.RAINFOREST_MAX_RESULTS:
                    break
            if len(rows) >= config.RAINFOREST_MAX_RESULTS:
                break
        if len(rows) >= config.RAINFOREST_MAX_RESULTS:
            break

    rows = beverages.dedupe_asins(rows)[: config.RAINFOREST_MAX_RESULTS]

    opportunities: list[dict[str, Any]] = []
    trends_ok = 0
    for row in rows:
        asin = row["asin"]
        try:
            prod = rf.product(asin)
        except Exception as e:
            LOG.info("Rainforest product %s: %s", asin, e)
            continue
        if not prod:
            continue
        amazon = rf.parse_product_row(prod)
        if not beverages.is_likely_beverage_title(amazon["title"]):
            continue

        kw = _short_kw(amazon["title"])
        tr = trends_client.fetch_interest(kw)
        if tr.get("ok"):
            trends_ok += 1

        wm = walmart_client.search_product(kw)
        rd = reddit_client.search_mentions(kw)

        meta = scoring.build_opportunity(amazon, tr, wm, rd)
        bev_type = beverages.classify_beverage_type(amazon["title"])
        ap = amazon.get("price")
        if isinstance(ap, (int, float)) and ap > 0:
            lo = round(float(ap) * 0.82, 2)
            hi = round(float(ap) * 1.12, 2)
            price_band = f"${lo} – ${hi} retail-comparable (Amazon anchor ${round(float(ap), 2)})"
        else:
            price_band = "Anchor Amazon price unavailable — validate comps manually."

        opportunities.append(
            {
                "id": asin,
                "asin": asin,
                "title": amazon["title"],
                "beverage_type": bev_type,
                "image": amazon.get("image") or row.get("image") or "",
                "description": (
                    f"{amazon['title']} — tracked as a beverage SKU on {config.AMAZON_DOMAIN}. "
                    f"Opportunity blends Amazon listing strength, US search interest, Walmart parity (if found), "
                    f"and recent Reddit mentions."
                ),
                "buyer": {
                    "sourcing_strategy": (
                        "Lead manufacturers with Amazon BSR + Google Trends corroboration; "
                        "use Reddit quotes as qualitative demand checks, not proof of sell-through."
                    ),
                    "suggested_price_range": price_band,
                    "target_channels": ["Amazon US", "Club", "Convenience", "Foodservice"],
                    "risk_level": (meta.get("risk") or {}).get("level", "Medium"),
                },
                "amazon": {
                    "price": amazon.get("price"),
                    "rating": amazon.get("rating"),
                    "reviews": amazon.get("reviews"),
                    "bsr": amazon.get("bsr"),
                    "url": amazon.get("url"),
                },
                "google_trends": {
                    "keyword": tr.get("keyword"),
                    "interest_index": tr.get("interest_index"),
                    "change_note": tr.get("change_note"),
                    "ok": bool(tr.get("ok")),
                },
                "walmart": wm,
                "reddit": {
                    "mentions": rd.get("mentions"),
                    "signal": rd.get("signal"),
                    "velocity_label": rd.get("velocity_label"),
                    "sample_titles": rd.get("posts") or [],
                    "score": rd.get("score"),
                    "subreddits_checked": rd.get("subreddits_checked"),
                },
                **meta,
            }
        )

    source_status["google_trends"] = "ok" if trends_ok else "degraded"
    source_status["walmart"] = (
        "ok"
        if (config.WALMART_KEY or (config.WALMART_CLIENT_ID and config.WALMART_CLIENT_SECRET))
        else "skipped_no_credentials"
    )
    source_status["reddit"] = "ok"

    opportunities.sort(key=lambda x: int(x.get("opportunity_score") or 0), reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "cache_ttl_hours": config.CACHE_TTL_HOURS,
        "source_status": source_status,
        "beverage_types": beverages.BEVERAGE_TYPES_ORDER,
        "opportunities": opportunities,
    }


def seed_demo_feed() -> dict[str, Any]:
    """Offline-friendly demo payload when API keys are missing."""
    opps: list[dict[str, Any]] = [
        {
            "id": "DEMO01",
            "asin": "DEMO01",
            "title": "Demo Electrolyte Sparkling Water — Variety Pack",
            "beverage_type": "Water & sparkling",
            "image": "",
            "description": "Illustrative row. Run the Python server with RAINFOREST_API_KEY to hydrate real ASINs.",
            "amazon": {
                "price": 24.99,
                "rating": 4.6,
                "reviews": 12840,
                "bsr": 42,
                "url": "https://www.amazon.com",
            },
            "google_trends": {
                "keyword": "electrolyte sparkling water",
                "interest_index": 78,
                "change_note": "Demo data",
                "ok": True,
            },
            "walmart": {
                "found": True,
                "walmart_count": 4,
                "gap": "low",
                "title": "Demo match — Electrolyte Sparkling 12pk",
                "price": 22.5,
                "item_id": "demo-wm",
                "url": "",
                "note": "Demo",
            },
            "reddit": {
                "mentions": 18,
                "signal": "high",
                "velocity_label": "active discussion (multi-subreddit)",
                "sample_titles": [
                    "Anyone tried the new electrolyte sparkling brand?",
                    "Best hydration seltzers this summer",
                ],
                "score": 72,
                "subreddits_checked": ["asianeats", "tea", "EatCheapAndHealthy"],
            },
            "opportunity_score": 81,
            "recommendation": "Watch",
            "headline_reason": "Demo: strong blended score with elevated social chatter.",
            "card_explanation": "Demo: strong blended score with elevated social chatter.",
            "explanation_bullets": [
                "Demo dataset — configure APIs for production.",
                "Risk is Medium in demo mix due to parity unknowns.",
            ],
            "trend_outlook": "Demo outlook: category interest up; confirm with live pulls.",
            "risk": {
                "level": "Medium",
                "factors": [
                    "Demo mode — replace with live Walmart + Reddit + Trends reads.",
                    "Ultra-competitive BSR band — incumbent-heavy.",
                ],
            },
            "buyer": {
                "sourcing_strategy": "Demo: negotiate on velocity + differentiation, not price alone.",
                "suggested_price_range": "$18 – $28 (illustrative)",
                "target_channels": ["Amazon US", "Specialty grocery"],
                "risk_level": "Medium",
            },
        },
        {
            "id": "DEMO02",
            "asin": "DEMO02",
            "title": "Demo Oat Milk Barista Blend 32oz",
            "beverage_type": "Dairy & plant milks",
            "image": "",
            "description": "Second illustrative beverage for filters and detail UX.",
            "amazon": {
                "price": 4.29,
                "rating": 4.3,
                "reviews": 920,
                "bsr": 210,
                "url": "https://www.amazon.com",
            },
            "google_trends": {
                "keyword": "oat milk barista",
                "interest_index": 55,
                "change_note": "Search interest roughly stable",
                "ok": True,
            },
            "walmart": {
                "found": False,
                "walmart_count": 0,
                "gap": "high",
                "note": "No catalog hits (demo)",
            },
            "reddit": {
                "mentions": 4,
                "signal": "med",
                "velocity_label": "light mentions across target subs",
                "sample_titles": ["Barista oat milk taste test"],
                "score": 44,
                "subreddits_checked": ["tea", "EatCheapAndHealthy"],
            },
            "opportunity_score": 52,
            "recommendation": "Watch",
            "headline_reason": "Demo: moderate opportunity with thinner social proof.",
            "card_explanation": "Demo: moderate opportunity with thinner social proof.",
            "explanation_bullets": [
                "Stable search with mid-tier Amazon reviews.",
                "Walmart parity not verified in demo.",
            ],
            "trend_outlook": "Demo outlook: steady niche; win on placement and formulation story.",
            "risk": {
                "level": "Low",
                "factors": ["Demo mode — trends only approximated here."],
            },
            "buyer": {
                "sourcing_strategy": "Demo: test-and-learn LTO before depth.",
                "suggested_price_range": "$3.50 – $5.50 (illustrative)",
                "target_channels": ["Grocery", "Cafe distributor"],
                "risk_level": "Low",
            },
        },
    ]

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cache_ttl_hours": config.CACHE_TTL_HOURS,
        "source_status": {
            "rainforest": "demo",
            "google_trends": "demo",
            "walmart": "demo",
            "reddit": "demo",
        },
        "beverage_types": beverages.BEVERAGE_TYPES_ORDER,
        "opportunities": opps,
    }
