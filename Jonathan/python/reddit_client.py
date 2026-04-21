"""Reddit public JSON: per-subreddit search (same pattern as prior arbitrage engine)."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

import config

LOG = logging.getLogger(__name__)


def _signal_from_mentions(mention_count: int) -> str:
    if mention_count > 10:
        return "high"
    if mention_count > 3:
        return "med"
    return "low"


def _velocity_from_signal(signal: str) -> str:
    if signal == "high":
        return "active discussion (multi-subreddit)"
    if signal == "med":
        return "light mentions across target subs"
    return "few recent posts in target subs"


def get_reddit_signal(product_name: str) -> dict[str, Any]:
    """
    Search fixed beverage-relevant subreddits for the product name.
    No Reddit API key — uses public search.json + User-Agent.
    """
    q = (product_name or "").strip()
    if len(q) < 2:
        return {
            "mentions": 0,
            "signal": "low",
            "posts": [],
            "velocity_label": "none",
            "score": 0,
        }

    headers = {"User-Agent": config.REDDIT_USER_AGENT}
    per_sub_limit = max(1, min(25, int(config.REDDIT_SUB_LIMIT)))
    max_subs = max(1, int(config.REDDIT_MAX_SUBREDDITS))
    max_mentions = max(1, int(config.REDDIT_MAX_TOTAL_MENTIONS))
    max_titles = max(1, int(config.REDDIT_MAX_SAMPLE_TITLES))
    mention_count = 0
    titles: list[str] = []
    seen: set[str] = set()
    checked_subs: list[str] = []

    for sub in config.REDDIT_SUBREDDITS[:max_subs]:
        checked_subs.append(sub)
        url = f"https://www.reddit.com/r/{sub}/search.json"
        params: dict[str, str | int] = {
            "q": q[:200],
            "limit": per_sub_limit,
            "sort": "new",
            "restrict_sr": 1,
            "raw_json": 1,
        }
        try:
            r = requests.get(url, headers=headers, params=params, timeout=12)
            r.raise_for_status()
            payload = r.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            children = (data.get("children") if isinstance(data, dict) else None) or []
            if isinstance(children, list):
                mention_count += len(children)
                for ch in children:
                    if not isinstance(ch, dict):
                        continue
                    d = ch.get("data")
                    if not isinstance(d, dict):
                        continue
                    t = d.get("title")
                    if isinstance(t, str):
                        s = t.strip()[:180]
                        if s and s not in seen:
                            seen.add(s)
                            titles.append(s)
                    if len(titles) >= max_titles:
                        break
        except Exception as e:
            LOG.info("Reddit r/%s search failed: %s", sub, e)
        if mention_count >= max_mentions:
            break
        if config.REDDIT_SUB_SLEEP_SEC > 0:
            time.sleep(config.REDDIT_SUB_SLEEP_SEC)

    mention_count = min(mention_count, max_mentions)
    signal = _signal_from_mentions(mention_count)
    score = float(min(100, 12 + mention_count * 2.8))
    return {
        "mentions": mention_count,
        "signal": signal,
        "posts": titles[:max_titles],
        "velocity_label": _velocity_from_signal(signal),
        "score": score,
        "subreddits_checked": checked_subs,
    }


def search_mentions(query: str, limit: int = 15) -> dict[str, Any]:
    """Pipeline entry point — wraps get_reddit_signal for a search phrase."""
    _ = limit  # retained for API compatibility
    out = get_reddit_signal(query)
    if out.get("mentions") == 0 and not out.get("posts"):
        out.setdefault("velocity_label", "few recent posts in target subs")
    return out
