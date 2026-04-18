"""Google Trends via pytrends (unofficial). Degrades gracefully if unavailable."""

from __future__ import annotations

import logging
from typing import Any

LOG = logging.getLogger(__name__)


def fetch_interest(keyword: str) -> dict[str, Any]:
    """
    Returns interest_index 0-100 (recent mean), change note, and raw series length.
    """
    kw = (keyword or "").strip()
    if len(kw) < 2:
        return {
            "keyword": kw,
            "interest_index": 0,
            "change_note": "No keyword",
            "ok": False,
        }
    try:
        from pytrends.request import TrendReq  # type: ignore
    except Exception as e:  # pragma: no cover
        LOG.warning("pytrends not available: %s", e)
        return {
            "keyword": kw[:80],
            "interest_index": 50,
            "change_note": "pytrends not installed — pip install pytrends",
            "ok": False,
        }

    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pytrends.build_payload([kw[:100]], timeframe="today 3-m", geo="US")
        df = pytrends.interest_over_time()
        if df is None or df.empty or kw[:100] not in df.columns:
            return {
                "keyword": kw[:80],
                "interest_index": 45,
                "change_note": "No trend series returned",
                "ok": True,
            }
        series = df[kw[:100]].astype(float)
        tail = series.tail(14).mean()
        head = series.head(14).mean()
        idx = int(round(min(100, max(0, float(tail)))))
        delta = float(tail) - float(head) if head else 0.0
        if delta > 8:
            note = "Search interest rising vs quarter start"
        elif delta < -8:
            note = "Search interest cooling vs quarter start"
        else:
            note = "Search interest roughly stable"
        return {
            "keyword": kw[:80],
            "interest_index": idx,
            "change_note": note,
            "ok": True,
        }
    except Exception as e:
        LOG.info("Trends fetch failed for %r: %s", kw[:40], e)
        return {
            "keyword": kw[:80],
            "interest_index": 40,
            "change_note": f"Trends unavailable ({type(e).__name__})",
            "ok": False,
        }
