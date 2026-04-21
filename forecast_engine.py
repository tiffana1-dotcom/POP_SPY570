"""
30-Day Opportunity Forecast — rule-based seasonal + event signals for buyers.

Not a prediction of sales; combines current listing strength with configurable
calendar rules and tag overlap. Tune weights in config/event_tag_weights.json
and calendars in config/seasonal_events.json.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

CONFIG_DIR = Path(__file__).resolve().parent / "config"


def load_seasonal_events(path: Path | None = None) -> dict[str, Any]:
    p = path or (CONFIG_DIR / "seasonal_events.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_category_rules(path: Path | None = None) -> dict[str, Any]:
    p = path or (CONFIG_DIR / "category_rules.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_event_tag_weights(path: Path | None = None) -> dict[str, Any]:
    p = path or (CONFIG_DIR / "event_tag_weights.json")
    if not p.is_file():
        return {
            "weights": {
                "current_opportunity": 0.34,
                "event_tag_overlap": 0.22,
                "seasonal_category_fit": 0.18,
                "validation_rating_reviews": 0.16,
                "rank_bonus": 0.10,
            }
        }
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Date helpers (US-centric holidays; extend for other markets)
# ---------------------------------------------------------------------------


def _weekday_mon0(d: date) -> int:
    return d.weekday()  # Mon=0 .. Sun=6


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """weekday: Mon=0..Sun=6; n=1 first, 2 second, ..."""
    d = date(year, month, 1)
    # days until first weekday
    delta = (weekday - _weekday_mon0(d) + 7) % 7
    first = d + timedelta(days=delta)
    return first + timedelta(weeks=n - 1)


def _second_sunday_may(year: int) -> date:
    return _nth_weekday_of_month(year, 5, 6, 2)  # Sunday=6


def _third_sunday_june(year: int) -> date:
    return _nth_weekday_of_month(year, 6, 6, 3)


def _fourth_thursday_november(year: int) -> date:
    return _nth_weekday_of_month(year, 11, 3, 4)  # Thu=3


def _date_range_intersects(a0: date, a1: date, b0: date, b1: date) -> bool:
    return not (a1 < b0 or b1 < a0)


def _in_months(d: date, months: list[int]) -> bool:
    return d.month in months


def _season_active_in_horizon(
    today: date, horizon_end: date, months: list[int], days_before: int
) -> tuple[bool, str]:
    """
    True if any day in [today, horizon_end] falls in `months`, OR the horizon
    overlaps the lead-in window before the next 1st-of-month that starts an in-season month.
    """
    months_set = set(int(x) for x in months)
    d = today
    while d <= horizon_end:
        if d.month in months_set:
            return True, "in_season"
        d += timedelta(days=1)

    # Lead-in: e.g. Spring — overlap with [Mar 1 - days_before, Feb last] etc.
    for yr in (today.year, today.year + 1):
        for m in sorted(months_set):
            try:
                start = date(yr, m, 1)
            except ValueError:
                continue
            if start <= today:
                continue
            lead_start = start - timedelta(days=days_before)
            if _date_range_intersects(today, horizon_end, lead_start, start - timedelta(days=1)):
                return True, "lead_in"
    return False, ""


def _holiday_in_horizon(
    today: date, horizon_end: date, holiday_key: str, days_before: int
) -> tuple[bool, date | None, str]:
    """Returns (active, anchor_date, reason)."""
    y = today.year
    anchors: list[date] = []

    if holiday_key == "second_sunday_may":
        anchors = [_second_sunday_may(y), _second_sunday_may(y + 1)]
    elif holiday_key == "third_sunday_june":
        anchors = [_third_sunday_june(y), _third_sunday_june(y + 1)]
    elif holiday_key == "fourth_thursday_november":
        anchors = [_fourth_thursday_november(y), _fourth_thursday_november(y + 1)]
    else:
        return False, None, ""

    for h in anchors:
        win_start = h - timedelta(days=days_before)
        win_end = h
        if _date_range_intersects(today, horizon_end, win_start, win_end):
            return True, h, "pre_holiday_window"
        # also if holiday falls inside horizon
        if today <= h <= horizon_end:
            return True, h, "holiday_in_horizon"

    return False, None, ""


def _fixed_month_day_in_horizon(
    today: date, horizon_end: date, month: int, day: int, days_before: int
) -> tuple[bool, date | None]:
    candidates: list[date] = []
    for yr in (today.year - 1, today.year, today.year + 1):
        try:
            candidates.append(date(yr, month, day))
        except ValueError:
            continue
    for h in candidates:
        win_start = h - timedelta(days=days_before)
        if _date_range_intersects(today, horizon_end, win_start, h):
            return True, h
        if today <= h <= horizon_end:
            return True, h
    return False, None


def _range_in_horizon(
    today: date,
    horizon_end: date,
    sm: int,
    sd: int,
    em: int,
    ed: int,
) -> bool:
    """Inclusive range within a year; handles wrap by checking both years."""
    y = today.year
    for year in (y, y + 1):
        try:
            start = date(year, sm, sd)
            end = date(year, em, ed)
            if start > end:
                # wrap (e.g. Nov–Jan) — skip generic; use two checks
                continue
            if _date_range_intersects(today, horizon_end, start, end):
                return True
        except ValueError:
            continue
    return False


def get_upcoming_events(today: date | None = None, days_ahead: int = 30) -> list[dict[str, Any]]:
    """
    Return event definitions that are relevant on the horizon [today, today+days_ahead].
    Each item includes the base event dict plus computed fields: anchor_date, relevance_reason.
    """
    if today is None:
        today = date.today()
    horizon_end = today + timedelta(days=days_ahead)
    data = load_seasonal_events()
    events = data.get("events", [])
    out: list[dict[str, Any]] = []

    for ev in events:
        wl = ev.get("window_logic") or {}
        days_before = int(ev.get("window_days_before", 14))
        active = False
        anchor: date | None = None
        reason = ""

        if "months" in wl:
            months = [int(x) for x in wl["months"]]
            ok, reason = _season_active_in_horizon(today, horizon_end, months, days_before)
            active = ok
            if active:
                anchor = today

        elif "holiday" in wl:
            hk = str(wl["holiday"])
            ok, ad, reason = _holiday_in_horizon(today, horizon_end, hk, days_before)
            active = ok
            anchor = ad

        elif "month_day" in wl:
            md = wl["month_day"]
            m, d = int(md["month"]), int(md["day"])
            ok, ad = _fixed_month_day_in_horizon(today, horizon_end, m, d, days_before)
            active = ok
            anchor = ad

        elif "month_day_range" in wl:
            r = wl["month_day_range"]
            active = _range_in_horizon(
                today,
                horizon_end,
                int(r["start_month"]),
                int(r["start_day"]),
                int(r["end_month"]),
                int(r["end_day"]),
            )
            if active:
                anchor = today
                reason = "range_overlap"

        if not active:
            continue

        row = dict(ev)
        row["_anchor_date"] = anchor.isoformat() if anchor else ""
        row["_relevance_reason"] = reason
        out.append(row)

    # Cap for scoring clarity
    wcfg = load_event_tag_weights()
    cap = int(wcfg.get("max_events_considered", 6))
    return out[:cap] if len(out) > cap else out


# ---------------------------------------------------------------------------
# Normalization & tags
# ---------------------------------------------------------------------------


def _blob_from_row(row: pd.Series | dict[str, Any]) -> str:
    parts: list[str] = []
    if isinstance(row, pd.Series):
        title = str(row.get("amazon_title") or row.get("search_result_title") or "")
        q = str(row.get("query") or "")
        ben = str(row.get("product_benefits") or "")
        bullets = row.get("bullets") or []
        item = row.get("item_details") or {}
    else:
        title = str(row.get("amazon_title") or row.get("search_result_title") or "")
        q = str(row.get("query") or "")
        ben = str(row.get("product_benefits") or "")
        bullets = row.get("bullets") or []
        item = row.get("item_details") or {}
    parts.extend([title, q, ben])
    if isinstance(bullets, list):
        parts.extend(str(b) for b in bullets)
    if isinstance(item, dict):
        parts.extend(f"{k} {v}" for k, v in item.items() if v)
    return " \n ".join(parts).lower()


def normalize_product(row: pd.Series) -> dict[str, Any]:
    """Defensive normalized view for forecasting."""
    title = str(row.get("amazon_title") or row.get("search_result_title") or "").strip()
    q = str(row.get("query") or "").strip()
    price = row.get("price_num")
    try:
        price_value = float(price) if pd.notna(price) else float("nan")
    except (TypeError, ValueError):
        price_value = float("nan")
    rating = row.get("rating")
    try:
        rating_value = float(rating) if pd.notna(rating) else float("nan")
    except (TypeError, ValueError):
        rating_value = float("nan")
    try:
        review_count_value = int(row.get("review_count") or 0)
    except (TypeError, ValueError):
        review_count_value = 0
    try:
        search_rank_value = float(row.get("search_result_rank_used") or 99)
    except (TypeError, ValueError):
        search_rank_value = 99.0
    ben = _clean_str(row.get("product_benefits"))
    shelf = _clean_str(row.get("product_shelf_life"))
    bullets = row.get("bullets") if isinstance(row.get("bullets"), list) else []
    bullets_text = " ".join(str(b) for b in bullets[:12])
    brand = ""
    it = row.get("item_details")
    if isinstance(it, dict):
        for k, v in it.items():
            if "brand" in k.lower() and v:
                brand = str(v).strip()[:120]
                break
    category = _infer_category_bucket(title, q, bullets_text, ben)
    return {
        "title": title,
        "query": q,
        "category": category,
        "price_value": price_value,
        "rating_value": rating_value,
        "review_count_value": review_count_value,
        "search_rank_value": search_rank_value,
        "bullets_text": bullets_text,
        "benefits_text": ben,
        "shelf_life_text": shelf,
        "brand": brand,
        "opportunity_score": float(row.get("opportunity_score") or 0),
        "asin": str(row.get("asin") or ""),
    }


def _clean_str(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return str(x).strip()


def _infer_category_bucket(title: str, query: str, bullets: str, benefits: str) -> str:
    blob = f"{title} {query} {bullets} {benefits}".lower()
    rules = load_category_rules()
    best = "general"
    best_len = 0
    for row in rules.get("query_to_category", []):
        for p in row.get("patterns", []):
            if p.lower() in blob and len(p) > best_len:
                best = row["category"]
                best_len = len(p)
    for row in rules.get("title_category_hints", []):
        for p in row.get("patterns", []):
            if p.lower() in title.lower() and len(p) > best_len:
                best = row["category"]
                best_len = len(p)
    return best


def infer_product_tags(row: pd.Series | dict[str, Any]) -> set[str]:
    """Keyword-driven tags from title, query, bullets, benefits, item_details."""
    rules = load_category_rules()
    blob = _blob_from_row(row)
    tags: set[str] = set()
    for m in rules.get("keyword_to_tags", []):
        for kw in m.get("keywords", []):
            if kw.lower() in blob:
                tags.update(m.get("tags", []))
    # category-derived
    if isinstance(row, pd.Series):
        cat = normalize_product(row)["category"]
    else:
        cat = _infer_category_bucket(
            str(row.get("amazon_title") or ""),
            str(row.get("query") or ""),
            str(row.get("bullets") or ""),
            str(row.get("product_benefits") or ""),
        )
    if cat and cat != "general":
        tags.add(cat.replace(" ", "-"))
    return tags


def score_product_for_event(
    product_tags: Iterable[str],
    category: str,
    event: dict[str, Any],
) -> float:
    """0–1 overlap strength between product tags and event tags/categories."""
    ptags = {t.lower() for t in product_tags}
    etags = {t.lower() for t in event.get("relevant_tags", [])}
    bcats = {c.lower() for c in event.get("boosted_categories", [])}
    if not etags and not bcats:
        return 0.0
    tag_hits = len(ptags & etags) / max(1, len(etags))
    cat_hit = 1.0 if category.lower() in bcats else 0.0
    if not ptags & etags:
        tag_hits = 0.0
    return float(np.clip(0.55 * tag_hits + 0.45 * cat_hit, 0.0, 1.0))


def _validation_signal(norm: dict[str, Any]) -> float:
    """0–1 from rating + review volume (social proof for near-term lift)."""
    r = norm["rating_value"]
    rev = norm["review_count_value"]
    if math.isnan(r):
        r = 3.5
    r_part = (r / 5.0) * 0.55
    rev_part = min(1.0, math.log1p(max(0, rev)) / math.log1p(50_000)) * 0.45
    return float(np.clip(r_part + rev_part, 0.0, 1.0))


def _rank_signal(search_rank: float) -> float:
    """Better organic rank → slightly higher signal (bounded)."""
    r = min(max(search_rank, 1.0), 50.0)
    return float(np.clip(1.0 - (r - 1.0) / 49.0, 0.0, 1.0))


def compute_future_opportunity(
    norm: dict[str, Any],
    product_tags: set[str],
    upcoming_events: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> tuple[float, list[dict[str, Any]], float]:
    """
    Returns (future_score 0–100, per-event contributions for explainability, best_event_score).

    Scoring (0–1 components, then ×100):
      combined = w_cur * current_opp
             + w_ev * best_event_tag_match
             + w_se * mean(top-2 event overlaps)  # seasonal_fit proxy
             + w_val * validation_signal(rating, reviews)
             + w_rank * search_rank_signal

    Tune weights in config/event_tag_weights.json; adjust calendars in seasonal_events.json.
    """
    wcfg = load_event_tag_weights()
    w = weights or wcfg.get("weights", {})
    w_cur = float(w.get("current_opportunity", 0.34))
    w_ev = float(w.get("event_tag_overlap", 0.22))
    w_se = float(w.get("seasonal_category_fit", 0.18))
    w_val = float(w.get("validation_rating_reviews", 0.16))
    w_rank = float(w.get("rank_bonus", 0.10))

    current = np.clip(norm["opportunity_score"] / 100.0, 0.0, 1.0)
    val = _validation_signal(norm)
    rnk = _rank_signal(norm["search_rank_value"])

    event_scores: list[tuple[dict[str, Any], float]] = []
    for ev in upcoming_events:
        s = score_product_for_event(product_tags, norm["category"], ev)
        event_scores.append((ev, s))

    best_event_score = max((s for _, s in event_scores), default=0.0)
    # Seasonal fit: average of top-2 event overlaps to reduce noise
    top_two = sorted((s for _, s in event_scores), reverse=True)[:2]
    seasonal_fit = float(np.mean(top_two)) if top_two else 0.0

    # Combined 0–1
    combined = (
        w_cur * current
        + w_ev * best_event_score
        + w_se * seasonal_fit
        + w_val * val
        + w_rank * rnk
    )
    future = float(np.clip(combined * 100.0, 0.0, 100.0))

    contributions = [
        {"event_id": ev["id"], "event_name": ev["name"], "match_strength": round(s, 3)}
        for ev, s in event_scores
        if s > 0.05
    ]
    contributions.sort(key=lambda x: -x["match_strength"])
    return future, contributions[:5], best_event_score


def _forecast_label(score: float, best_event: float, n_events: int) -> str:
    if n_events == 0:
        return "Watchlist"
    if score >= 72 and best_event >= 0.45:
        return "Rising Opportunity"
    if score >= 62 and best_event >= 0.35:
        return "Event-Driven Potential"
    if score >= 55:
        return "Seasonal Fit"
    if score >= 42:
        return "Watchlist"
    return "Low Near-Term Signal"


def _confidence(best_event: float, val: float) -> str:
    x = 0.5 * best_event + 0.5 * val
    if x >= 0.55:
        return "High"
    if x >= 0.35:
        return "Medium"
    return "Low"


def build_forecast_summary(
    norm: dict[str, Any],
    product_tags: set[str],
    upcoming_events: list[dict[str, Any]],
    future_score: float,
    contributions: list[dict[str, Any]],
    best_event_score: float,
) -> dict[str, Any]:
    """Narrative + structured fields for UI."""
    val = _validation_signal(norm)
    names = [e["name"] for e in upcoming_events][:4]
    top_ev = upcoming_events[0] if upcoming_events else None

    reasons: list[str] = []
    if top_ev:
        tmpl = top_ev.get("explanation_template", "")
        tag_sample = ", ".join(sorted(list(product_tags)[:4])) if product_tags else "its category cues"
        try:
            blurb = tmpl.format(tags=tag_sample)
        except Exception:
            blurb = tmpl or "Event-aligned assortment signal based on listing text and calendar rules."
        reasons.append(blurb)
    if norm["opportunity_score"] >= 55:
        reasons.append("Current listing strength suggests a credible near-term signal worth watching.")
    if val >= 0.55:
        reasons.append("Ratings and review volume add validation for shelf conversations.")
    if not reasons:
        reasons.append("Limited overlap with upcoming calendar drivers; treat as exploratory.")

    buyer_action = (
        "Consider a small buy or placement test if distribution slots align with the relevant season."
    )
    if future_score >= 68:
        buyer_action = "Worth prioritizing for assortment review: calendar fit plus solid listing validation."
    elif future_score < 45:
        buyer_action = "Keep on watchlist; confirm velocity and promo plans before committing depth."

    label = _forecast_label(future_score, best_event_score, len(upcoming_events))
    conf = _confidence(best_event_score, val)

    badges: list[str] = []
    for ev in upcoming_events[:4]:
        bl = ev.get("badge_label")
        if bl:
            badges.append(str(bl))
    # dedupe preserve order
    seen: set[str] = set()
    badges_u = [b for b in badges if not (b in seen or seen.add(b))]

    expl = reasons[0] if reasons else "Rule-based forward signal; not a demand forecast."
    expl = _sanitize_buyer_tone(expl)

    return {
        "future_opportunity_score": round(future_score, 1),
        "forecast_label": label,
        "relevant_upcoming_events": names,
        "seasonal_fit": "Strong" if best_event_score >= 0.45 else ("Moderate" if best_event_score >= 0.25 else "Limited"),
        "future_reasons": [_sanitize_buyer_tone(r) for r in reasons[:4]],
        "buyer_action": _sanitize_buyer_tone(buyer_action),
        "forecast_confidence": conf,
        "event_badges": badges_u[:5],
        "event_driver": top_ev["name"] if top_ev else "—",
        "contributions": contributions,
    }


def _sanitize_buyer_tone(text: str) -> str:
    """Avoid absolute claims; keep wholesale buyer voice."""
    t = text
    bad = ["guaranteed", "certain", "definitive", "will spike", "sure winner"]
    for b in bad:
        t = re.sub(re.escape(b), "possible lift", t, flags=re.I)
    return t


def forecast_row(row: pd.Series, upcoming: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Full forecast dict for one product row."""
    if upcoming is None:
        upcoming = get_upcoming_events()
    norm = normalize_product(row)
    tags = infer_product_tags(row)
    fs, contribs, best_ev = compute_future_opportunity(norm, tags, upcoming)
    summary = build_forecast_summary(norm, tags, upcoming, fs, contribs, best_ev)
    summary["derived_tags"] = sorted(tags)
    summary["normalized"] = norm
    return summary


def attach_forecast_to_dataframe(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """
    Returns (df with forecast columns, upcoming events, full forecast dict by ASIN for detail UI).
    """
    if df.empty:
        return df, [], {}
    upcoming = get_upcoming_events()
    out = df.reset_index(drop=True).copy()
    by_asin: dict[str, dict[str, Any]] = {}
    f_scores: list[float] = []
    f_labels: list[str] = []
    f_conf: list[str] = []
    f_action: list[str] = []
    f_expl: list[str] = []
    f_badges: list[list[str]] = []
    f_events: list[list[str]] = []
    for _, row in out.iterrows():
        fr = forecast_row(row, upcoming)
        aid = str(row.get("asin") or "")
        by_asin[aid] = fr
        f_scores.append(float(fr["future_opportunity_score"]))
        f_labels.append(str(fr["forecast_label"]))
        f_conf.append(str(fr["forecast_confidence"]))
        f_action.append(str(fr["buyer_action"]))
        expl = fr["future_reasons"][0] if fr.get("future_reasons") else ""
        f_expl.append(expl)
        f_badges.append(list(fr.get("event_badges") or []))
        f_events.append(list(fr.get("relevant_upcoming_events") or []))
    out["future_opportunity_score"] = f_scores
    out["forecast_label"] = f_labels
    out["forecast_confidence"] = f_conf
    out["forecast_buyer_action"] = f_action
    out["forecast_explanation"] = f_expl
    out["forecast_badges"] = f_badges
    out["forecast_events"] = f_events
    return out, upcoming, by_asin


def top_forecast_products(df: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    """Sort by future_opportunity_score descending."""
    if df.empty or "future_opportunity_score" not in df.columns:
        return df.head(0)
    return df.sort_values("future_opportunity_score", ascending=False).head(n)
