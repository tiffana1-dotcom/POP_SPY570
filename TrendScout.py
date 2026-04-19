"""
SipScope Live — Streamlit buyer dashboard.
Loads product rows from FINAL.json (same folder as this file).
Run: streamlit run SipScope.py
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

import env_setup

env_setup.load_pop_dotenv()

from buyer_copilot import analyze_product, format_product_context_for_analysis
from copilot_page import render_copilot_gpt_result
from forecast_engine import attach_forecast_to_dataframe, top_forecast_products
from tariff_filter import flag_trade_risk
from sipscope_sidebar import SORT_LABELS, render_explore_sidebar

# Global master–detail selection (Forecast, Priority queue, All results share this).
SELECTED_PRODUCT_KEY = "selected_product"
DETAIL_OPEN_KEY = "detail_open"


def _close_detail_panel() -> None:
    st.session_state[DETAIL_OPEN_KEY] = False
    st.session_state[SELECTED_PRODUCT_KEY] = None


def _sync_detail_selection(fdf: pd.DataFrame) -> None:
    """Keep selected row in sync with filtered data; close detail if the SKU is gone."""
    if not st.session_state.get(DETAIL_OPEN_KEY):
        return
    sp = st.session_state.get(SELECTED_PRODUCT_KEY)
    if fdf.empty or not isinstance(sp, dict) or not sp:
        _close_detail_panel()
        return
    for i in range(len(fdf)):
        if _same_listing_row(fdf.iloc[i], sp):
            st.session_state[SELECTED_PRODUCT_KEY] = row_to_selected_product(fdf.iloc[i])
            return
    _close_detail_panel()


def _one_line_summary(row: pd.Series, fr: dict | None) -> str:
    if fr:
        reasons = fr.get("future_reasons") or []
        if reasons and str(reasons[0]).strip():
            s = str(reasons[0]).strip()
            return (s[:140] + "…") if len(s) > 143 else s
    bullets = row.get("bullets") or []
    if isinstance(bullets, list) and bullets:
        s = str(bullets[0]).strip()
        return (s[:140] + "…") if len(s) > 143 else s
    ben = row.get("product_benefits")
    if ben is not None and str(ben).strip():
        s = _clean_text_field(ben)
        return (s[:140] + "…") if len(s) > 143 else s
    return "—"


def _json_safe_value(v: Any) -> Any:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, (np.integer, np.floating)):
        return v.item()
    if hasattr(v, "item") and not isinstance(v, (bytes, str, dict, list)):
        try:
            return v.item()
        except Exception:
            pass
    if isinstance(v, (list, dict, str, bool, int, float)):
        return v
    return str(v)


def row_to_selected_product(row: pd.Series) -> dict[str, Any]:
    return {str(k): _json_safe_value(v) for k, v in row.items()}


def _same_listing_row(series: pd.Series, stored: dict | None) -> bool:
    if not stored:
        return False
    if str(series.get("asin") or "") != str(stored.get("asin") or ""):
        return False
    sq = str(series.get("query") or "")
    bq = str(stored.get("query") or "")
    su = str(series.get("url") or "")
    bu = str(stored.get("url") or "")
    if sq and bq and sq != bq:
        return False
    if su and bu and su != bu:
        return False
    return True


def _fdf_iloc_for_row(fdf: pd.DataFrame, row: pd.Series) -> int:
    """Index in fdf (0..len-1) for the same listing row (handles duplicate ASINs)."""
    a = str(row.get("asin") or "")
    q = str(row.get("query") or "")
    u = str(row.get("url") or "")
    for i in range(len(fdf)):
        r = fdf.iloc[i]
        if str(r.get("asin") or "") != a:
            continue
        if q and str(r.get("query") or "") != q:
            continue
        if u and str(r.get("url") or "") != u:
            continue
        return i
    for i in range(len(fdf)):
        if str(fdf.iloc[i].get("asin") or "") == a:
            return i
    return 0


# ---------------------------------------------------------------------------
# Commercial risk tier (heuristic — for filtering & badges, not legal advice)
# ---------------------------------------------------------------------------

RISK_LEVEL_OPTIONS: tuple[str, ...] = ("Low Risk", "Needs Review", "High Risk")


def estimate_risk_level(row: pd.Series) -> str:
    """Heuristic sourcing risk: listing quality + claim red-flag keywords."""
    r = row.get("rating")
    rating = float(r) if pd.notna(r) else 0.0
    rev = int(row.get("review_count") or 0)
    ben = str(row.get("product_benefits") or "").lower()
    bull = row.get("bullets")
    blob = ben
    if isinstance(bull, list):
        blob = (ben + " " + " ".join(str(x) for x in bull)).lower()
    red = (
        "fda approved",
        "fda cleared",
        "cure ",
        "cures",
        "treats disease",
        "diagnose",
        "miracle",
        "guaranteed results",
        "clinically proven",
        "lose weight fast",
    )
    if any(k in blob for k in red) or rating < 3.5 or (rating < 4.0 and rev < 25):
        return "High Risk"
    if rating < 4.35 or rev < 80 or (not str(row.get("product_shelf_life") or "").strip() and len(ben) < 8):
        return "Needs Review"
    return "Low Risk"


def risk_badge_class(tier: str) -> str:
    return {
        "Low Risk": "badge-risk badge-risk-low",
        "Needs Review": "badge-risk badge-risk-mid",
        "High Risk": "badge-risk badge-risk-high",
    }.get(tier, "badge-risk badge-risk-mid")


# ---------------------------------------------------------------------------
# Paths & data loading
# ---------------------------------------------------------------------------

DATA_FILE = Path(__file__).resolve().parent / "FINAL.json"

# Product benefits themes → keyword hints (matched on `product_benefits` text, case-insensitive).
# If multiple categories are selected, a row matches if it satisfies any selected theme (OR).
BENEFIT_CATEGORIES: dict[str, dict[str, object]] = {
    "low_calorie": {
        "label": "Low Calorie",
        "patterns": (
            "low calorie",
            "low-calorie",
            "zero calorie",
            "0 calorie",
            "calorie free",
            "sugar free",
            "no sugar",
            "less sugar",
            "reduced calorie",
        ),
    },
    "antioxidant_rich": {
        "label": "Antioxidant Rich",
        "patterns": (
            "antioxidant",
            "antioxidants",
            "polyphenol",
            "catechin",
            "egcg",
            "flavonoid",
        ),
    },
    "healthy_refreshment": {
        "label": "Healthy Refreshment",
        "patterns": (
            "refreshment",
            "refreshing",
            "hydration",
            "hydrating",
            "healthy refreshment",
            "replenish",
            "thirst",
        ),
    },
}


def row_matches_benefit_categories(row: pd.Series, selected_ids: list[str]) -> bool:
    """True if no filter, or Product benefits text matches any selected theme."""
    if not selected_ids:
        return True
    blob = str(row.get("product_benefits") or "").lower()
    if not blob.strip():
        return False
    for sid in selected_ids:
        meta = BENEFIT_CATEGORIES.get(sid)
        if not meta:
            continue
        patterns: tuple[str, ...] = meta["patterns"]  # type: ignore[assignment]
        if any(p in blob for p in patterns):
            return True
    return False


def _clean_text_field(val: object) -> str:
    """Normalize JSON null / empty to empty string for shelf life & benefits."""
    if val is None:
        return ""
    if isinstance(val, float) and pd.isna(val):
        return ""
    s = str(val).strip()
    return s


def _row_listing_facts(row: pd.Series) -> tuple[str, str, str, str]:
    """Shelf life, benefits, special ingredients, region of origin (normalized + raw keys)."""
    shelf = _clean_text_field(row.get("product_shelf_life"))
    if not shelf:
        shelf = _clean_text_field(row.get("Product Shelf Life"))
    ben = _clean_text_field(row.get("product_benefits"))
    if not ben:
        ben = _clean_text_field(row.get("Product Benefits"))
    ing = _clean_text_field(row.get("special_ingredients"))
    if not ing:
        ing = _clean_text_field(row.get("Special Ingredients"))
    region = _clean_text_field(row.get("region_of_origin"))
    if not region:
        region = _clean_text_field(row.get("Region of Origin"))
    if not region and isinstance(row.get("item_details"), dict):
        region = _clean_text_field((row.get("item_details") or {}).get("Region of Origin"))
    return shelf, ben, ing, region


def parse_price_to_float(price: object) -> float:
    if price is None or (isinstance(price, float) and np.isnan(price)):
        return float("nan")
    s = str(price).strip()
    if not s:
        return float("nan")
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def load_products(path: Path | None = None) -> pd.DataFrame:
    p = path or DATA_FILE
    if not p.exists():
        st.error(f"Data file not found: {p}")
        return pd.DataFrame()

    with open(p, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        st.error("Expected JSON array of products.")
        return pd.DataFrame()

    df = pd.DataFrame(raw)

    if "amazon_title" not in df.columns and "search_result_title" in df.columns:
        df["amazon_title"] = df["search_result_title"]

    df["price_num"] = df["price"].apply(parse_price_to_float)
    df["rating"] = pd.to_numeric(df.get("rating"), errors="coerce")
    df["review_count"] = pd.to_numeric(df.get("review_count"), errors="coerce").fillna(0).astype(int)
    df["search_result_rank_used"] = pd.to_numeric(
        df.get("search_result_rank_used"), errors="coerce"
    ).fillna(99)

    if "status" in df.columns:
        df_ok = df[df["status"].astype(str).str.lower() == "ok"].copy()
        if len(df_ok) > 0:
            df = df_ok

    df["bullets"] = df["bullets"].apply(
        lambda x: x if isinstance(x, list) else ([] if pd.isna(x) else [str(x)])
    )
    df["query"] = df.get("query", "").fillna("").astype(str)
    df["asin"] = df.get("asin", "").fillna("").astype(str)
    df["url"] = df.get("url", "").fillna("").astype(str)
    df["amazon_title"] = df.get("amazon_title", "").fillna("").astype(str)

    # Listing-derived fields (from scrape / JSON)
    if "Product Shelf Life" in df.columns:
        df["product_shelf_life"] = df["Product Shelf Life"].map(_clean_text_field)
    else:
        df["product_shelf_life"] = ""

    if "Product Benefits" in df.columns:
        df["product_benefits"] = df["Product Benefits"].map(_clean_text_field)
    else:
        df["product_benefits"] = ""

    if "Special Ingredients" in df.columns:
        df["special_ingredients"] = df["Special Ingredients"].map(_clean_text_field)
    else:
        df["special_ingredients"] = ""

    if "Region of Origin" in df.columns:
        df["region_of_origin"] = df["Region of Origin"].map(_clean_text_field)
    else:
        df["region_of_origin"] = ""

    df["opportunity_score"] = df.apply(compute_opportunity_score, axis=1)
    df["risk_level"] = df.apply(estimate_risk_level, axis=1)
    return df


# ---------------------------------------------------------------------------
# Scoring & reasons
# ---------------------------------------------------------------------------


def _tariff_score_multiplier(row: pd.Series) -> float:
    origin = str(row.get("region_of_origin") or row.get("Region of Origin") or "").strip()
    if origin.lower() in ("us", "usa", "u.s.", "u.s.a.", "united states of america"):
        origin = "United States"

    product_category = str(row.get("product_category") or row.get("category") or "").strip() or None
    try:
        trade_risk = flag_trade_risk(
            product_name=str(row.get("amazon_title") or row.get("search_result_title") or ""),
            country_of_origin=origin or "Unknown",
            product_category=product_category,
        )
        tier = int(trade_risk.get("tier", 1))
    except Exception:
        tier = 1

    return {
        0: 1.00,
        1: 0.96,
        2: 0.88,
        3: 0.72,
        4: 0.50,
    }.get(tier, 0.96)


def _tariff_risk_badge_html(row: pd.Series) -> str:
    origin = str(row.get("region_of_origin") or row.get("Region of Origin") or "").strip()
    if origin.lower() in ("us", "usa", "u.s.", "u.s.a.", "united states of america"):
        origin = "United States"

    product_category = str(row.get("product_category") or row.get("category") or "").strip() or None
    try:
        trade_risk = flag_trade_risk(
            product_name=str(row.get("amazon_title") or row.get("search_result_title") or ""),
            country_of_origin=origin or "Unknown",
            product_category=product_category,
        )
        tier = int(trade_risk.get("tier", 1))
        label = str(trade_risk.get("tier_label") or "Watch list")
    except Exception:
        tier = 1
        label = "Watch list"

    badge_cls = {
        0: "badge-risk badge-risk-low",
        1: "badge-risk badge-risk-mid",
        2: "badge-risk badge-risk-mid",
        3: "badge-risk badge-risk-high",
        4: "badge-risk badge-risk-high",
    }.get(tier, "badge-risk badge-risk-mid")

    return f'<span class="{badge_cls}">Tariff: {html.escape(label)}</span>'


def compute_opportunity_score(row: pd.Series) -> float:
    """Simple 0–100 score: rating, reviews, price, search rank."""
    r = row.get("rating")
    if pd.isna(r) or r is None:
        r = 0.0
    else:
        r = float(r)
    reviews = float(row.get("review_count") or 0)
    price = row.get("price_num")
    rank = float(row.get("search_result_rank_used") or 50)

    rating_pts = (r / 5.0) * 28.0
    review_pts = min(28.0, np.log1p(max(0, reviews)) / np.log1p(50000) * 28.0)

    if pd.isna(price) or price <= 0:
        price_pts = 10.0
    else:
        price_pts = min(22.0, 22.0 * (25.0 / (25.0 + float(price))))

    rank_pts = max(0.0, 22.0 * (1.0 - min(rank - 1.0, 24.0) / 24.0))
    base_score = float(np.clip(rating_pts + review_pts + price_pts + rank_pts, 0.0, 100.0))
    return float(np.clip(base_score * _tariff_score_multiplier(row), 0.0, 100.0))


def short_reasons(row: pd.Series) -> list[str]:
    reasons: list[str] = []
    r = row.get("rating")
    if pd.notna(r) and float(r) >= 4.5:
        reasons.append("High rating")
    rev = int(row.get("review_count") or 0)
    if rev >= 500:
        reasons.append("Strong review count")
    elif rev >= 100:
        reasons.append("Solid review volume")

    p = row.get("price_num")
    if pd.notna(p) and p <= 15:
        reasons.append("Good entry price")
    elif pd.notna(p) and p <= 35:
        reasons.append("Reasonable price point")

    rank = row.get("search_result_rank_used")
    if pd.notna(rank) and float(rank) <= 3:
        reasons.append("Strong search placement")

    if not reasons:
        reasons.append("Balanced signals vs. peers")
    return reasons[:4]


def top_recommendations(df_sorted: pd.DataFrame) -> pd.DataFrame:
    """Top 5 SKUs after the active sort (one row per ASIN, stable order)."""
    if df_sorted.empty:
        return df_sorted
    return df_sorted.drop_duplicates(subset=["asin"], keep="first").head(5)


def apply_filters(
    df: pd.DataFrame,
    q: str,
    queries: list[str],
    benefit_category_ids: list[str],
    min_rating: float,
    price_min: float,
    price_max: float,
) -> pd.DataFrame:
    out = df.copy()
    if q.strip():
        ql = q.lower()
        mask = (
            out["amazon_title"].str.lower().str.contains(ql, na=False)
            | out["query"].str.lower().str.contains(ql, na=False)
            | out["asin"].str.lower().str.contains(ql, na=False)
        )
        out = out[mask]
    if queries:
        out = out[out["query"].isin(queries)]
    if benefit_category_ids:
        out = out[out.apply(lambda r: row_matches_benefit_categories(r, benefit_category_ids), axis=1)]
    out = out[out["rating"].fillna(0) >= min_rating]
    pn = out["price_num"]
    out = out[pn.isna() | ((pn >= price_min) & (pn <= price_max))]
    return out


def _normalize_sort_key(raw: object) -> str:
    """Map sidebar value to internal keys (avoids silent no-op when key does not match)."""
    valid: tuple[str, ...] = tuple(SORT_LABELS.keys())
    if raw in valid:
        return str(raw)
    # Session / older builds: index into same option order as sidebar
    if isinstance(raw, int) and raw in range(len(valid)):
        return valid[raw]
    if isinstance(raw, str):
        t = raw.strip()
        if t in valid:
            return t
        tl = t.lower()
        for k, lab in SORT_LABELS.items():
            if lab.lower() == tl:
                return k
    return "best_opportunity"


def sort_dataframe(df: pd.DataFrame, sort_key: object) -> pd.DataFrame:
    """Sort filtered rows; secondary keys break ties so order is not arbitrary."""
    out = df.copy()
    if out.empty:
        return out

    key = _normalize_sort_key(sort_key)
    # Coerce so we never sort object/string columns lexicographically by accident.
    if "rating" in out.columns:
        out["rating"] = pd.to_numeric(out["rating"], errors="coerce")
    if "review_count" in out.columns:
        out["review_count"] = pd.to_numeric(out["review_count"], errors="coerce").fillna(0)
    if "price_num" in out.columns:
        out["price_num"] = pd.to_numeric(out["price_num"], errors="coerce")
    if "opportunity_score" in out.columns:
        out["opportunity_score"] = pd.to_numeric(out["opportunity_score"], errors="coerce").fillna(0)

    na_last: dict[str, Any] = {"na_position": "last"}
    if key == "highest_rating":
        return out.sort_values(
            ["rating", "review_count", "opportunity_score", "asin"],
            ascending=[False, False, False, True],
            **na_last,
        )
    if key == "most_reviews":
        return out.sort_values(
            ["review_count", "rating", "opportunity_score", "asin"],
            ascending=[False, False, False, True],
            **na_last,
        )
    if key == "lowest_price":
        return out.sort_values(
            ["price_num", "rating", "review_count", "asin"],
            ascending=[True, False, False, True],
            **na_last,
        )
    if key == "best_opportunity":
        return out.sort_values(
            ["opportunity_score", "review_count", "rating", "asin"],
            ascending=[False, False, False, True],
            **na_last,
        )
    return out.sort_values(
        ["opportunity_score", "review_count", "rating", "asin"],
        ascending=[False, False, False, True],
        **na_last,
    )


def filter_fingerprint(
    search: str,
    q_pick: list[str],
    benefit_pick: list[str],
    min_rating: float,
    pr_min: float,
    pr_max: float,
    n_filtered: int,
) -> str:
    return "|".join(
        [
            search.strip(),
            ",".join(sorted(q_pick)),
            ",".join(sorted(benefit_pick)),
            f"{min_rating:.2f}",
            f"{pr_min:.2f}",
            f"{pr_max:.2f}",
            str(n_filtered),
        ]
    )


def price_display(row: pd.Series) -> str:
    if isinstance(row.get("price"), str) and row.get("price"):
        return str(row["price"])
    if pd.notna(row.get("price_num")):
        return f"${float(row['price_num']):.2f}"
    return "—"


# ---------------------------------------------------------------------------
# UI — CSS (premium B2B sourcing — minimal, neutral)
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  :root {
    --bg: #f4f7f9;
    --surface: #ffffff;
    --line: #dfe1e6;
    --line-strong: #c1c7d0;
    --text: #172b4d;
    --hero-navy: #091e42;
    --text-2: #42526e;
    --text-3: #5e6c84;
    --primary: #0052cc;
    --primary-hover: #0747a6;
    --primary-soft: #deebff;
    --accent: #0052cc;
    --accent-soft: #f4f5f7;
    --success-bg: #ecfdf5;
    --success-border: #a7f3d0;
    --success-text: #065f46;
    --warn-bg: #fffbeb;
    --warn-border: #fde68a;
    --warn-text: #92400e;
    --tag-gray-bg: #f1f5f9;
    --tag-gray-text: #475569;
    --font: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    --space-xs: 8px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --radius-card: 8px;
    --radius-pill: 999px;
  }
  .stApp {
    background: var(--bg) !important;
    font-family: var(--font) !important;
    color: var(--text) !important;
  }
  /* Inline hero — no card; sits on page background */
  .ts-page-hero {
    margin: 0 0 2rem 0;
    padding: 0.25rem 0 0.5rem 0;
  }
  h1.ts-hero-title {
    font-size: clamp(2.125rem, 2.8vw, 2.75rem) !important;
    font-weight: 700 !important;
    letter-spacing: -0.045em !important;
    color: var(--hero-navy) !important;
    margin: 0 0 0.5rem 0 !important;
    line-height: 1.08 !important;
    font-family: var(--font) !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
  }
  p.ts-hero-tagline {
    font-size: 0.9375rem !important;
    font-weight: 400 !important;
    color: var(--text-3) !important;
    line-height: 1.55 !important;
    margin: 0 !important;
    max-width: 38rem !important;
    letter-spacing: 0.01em !important;
  }
  .main .block-container, section.main .block-container {
    font-size: 14px !important;
    line-height: 1.55 !important;
  }
  /* Default Streamlit header hidden — brand bar below */
  [data-testid="stHeader"] {
    display: none !important;
  }
  /* Built-in Streamlit sidebar hidden — filters render in the first main column */
  [data-testid="stSidebar"],
  section[data-testid="stSidebar"] {
    display: none !important;
  }
  [data-testid="collapsedControl"] {
    display: none !important;
  }
  [data-testid="stExpandSidebarButton"] {
    display: none !important;
  }
  [data-testid="stDecoration"] {
    display: none !important;
  }
  [data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  [data-testid="stAppViewContainer"] > section[data-testid="stMain"],
  section.main,
  .main {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  .block-container {
    padding-top: 2.25rem !important;
    padding-bottom: 5rem !important;
    max-width: min(1440px, 98vw) !important;
  }
  .main h1:not(.ts-hero-title) {
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    color: var(--text) !important;
    font-size: 1.75rem !important;
    line-height: 1.25 !important;
    font-family: var(--font) !important;
  }
  .subtitle {
    color: var(--text-3) !important;
    font-size: 0.9375rem !important;
    margin-top: 0 !important;
    line-height: 1.55 !important;
    max-width: 40rem !important;
    font-weight: 400 !important;
  }
  div[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-card) !important;
    padding: 1rem 1.15rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
  }
  div[data-testid="stMetric"] label {
    color: var(--text-3) !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
  }
  div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-weight: 600 !important;
  }
  .section-head {
    margin: 0 0 var(--space-xl) 0;
    padding-bottom: var(--space-md);
    border-bottom: 1px solid var(--line);
  }
  .section-head-k {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--text-3);
    font-weight: 600;
    margin: 0 0 var(--space-sm) 0;
  }
  .section-head-t {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.02em;
    margin: 0 0 var(--space-sm) 0;
    line-height: 1.3;
  }
  .section-head-s {
    font-size: 13px;
    color: var(--text-2);
    margin: 0;
    line-height: 1.55;
    max-width: 42rem;
  }
  .md-master {
    margin-top: 0.25rem;
  }
  div[data-testid="stRadio"] > div {
    gap: 0.4rem !important;
    flex-direction: column !important;
  }
  div[data-testid="stRadio"] > div > label {
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
    padding: 0.85rem 0.9rem 0.85rem 2.35rem !important;
    margin: 0 !important;
    transition: border-color 0.15s ease, background 0.15s ease !important;
    font-size: 0.8125rem !important;
    line-height: 1.45 !important;
    color: var(--text) !important;
    box-shadow: none !important;
  }
  div[data-testid="stRadio"] > div > label:hover {
    border-color: var(--line-strong) !important;
    background: #fafafa !important;
  }
  div[data-testid="stRadio"] > div > label:has(input:checked) {
    border-color: #93c5fd !important;
    background: var(--primary-soft) !important;
    box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.12) !important;
  }
  .detail-shell {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: var(--space-md) 1.25rem;
    min-height: 420px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  }
  .detail-kicker {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--text-3);
    font-weight: 600;
    margin-bottom: 0.65rem;
  }
  .detail-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.45;
    margin: 0 0 0.75rem 0;
    letter-spacing: -0.02em;
  }
  .detail-meta-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    margin-bottom: 1rem;
  }
  .score-pill-lg {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--primary);
    background: var(--primary-soft);
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 0.2rem 0.55rem;
    letter-spacing: 0.02em;
  }
  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.65rem 1rem;
    margin: 1rem 0;
    font-size: 13px;
  }
  .detail-grid.detail-grid--panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .dw-muted {
    font-size: 0.8125rem;
    color: var(--text-3);
    margin: 0;
    line-height: 1.5;
  }
  .dw-score-pair {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 0 0 12px 0;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--line);
  }
  .dw-score-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }
  .dw-sl {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-3);
    flex-shrink: 0;
  }
  .dw-sv { font-weight: 700; letter-spacing: -0.03em; }
  .dw-sv-forecast { font-size: 22px; color: var(--primary); }
  .dw-sv-current { font-size: 17px; font-weight: 600; color: #42526e; }
  .detail-grid div span.label {
    display: block;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-3);
    margin-bottom: 0.15rem;
  }
  .detail-grid div span.val {
    color: var(--text);
    font-weight: 500;
  }
  .detail-price {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.03em;
  }
  .detail-bullets {
    margin: 0.75rem 0 0 1rem;
    padding: 0;
    font-size: 0.8125rem;
    color: var(--text-2);
    line-height: 1.55;
  }
  .detail-bullets li { margin-bottom: 0.35rem; }
  .detail-extras {
    margin-top: 1.1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--line);
  }
  .detail-extras .extra-block { margin-bottom: 0.85rem; }
  .detail-extras .extra-block:last-child { margin-bottom: 0; }
  .detail-extras .extra-label {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3);
    font-weight: 600;
    margin-bottom: 0.3rem;
  }
  .detail-extras .extra-body {
    font-size: 0.8125rem;
    color: var(--text-2);
    line-height: 1.55;
    margin: 0;
  }
  .detail-extras .extra-body.muted { color: var(--text-3); font-style: normal; }
  .dw-card .detail-extras.dw-listing-detail-extras {
    margin-top: 0.35rem;
    padding-top: 0;
    border-top: none;
  }
  .detail-asin {
    font-size: 0.7rem;
    color: var(--text-3);
    font-family: ui-monospace, monospace;
    margin-top: 0.65rem;
  }
  .dw-overview .detail-asin {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--line);
  }
  .tag-pill {
    display: inline-block;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--tag-gray-text);
    background: var(--tag-gray-bg);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.2rem 0.5rem;
    margin-bottom: 0;
    font-weight: 600;
  }
  .badge-risk {
    display: inline-block;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.03em;
    border-radius: 8px;
    padding: 8px 14px;
    line-height: 1.2;
    border: 1.5px solid var(--line);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  }
  .badge-risk-low {
    color: #14532d;
    background: linear-gradient(180deg, #f0fdf4 0%, #ecfdf5 100%);
    border-color: #86efac;
  }
  .badge-risk-mid {
    color: #92400e;
    background: linear-gradient(180deg, #fffbeb 0%, #fef3c7 100%);
    border-color: #fcd34d;
  }
  .badge-risk-high {
    color: #57534e;
    background: linear-gradient(180deg, #fafaf9 0%, #f5f5f4 100%);
    border-color: #d6d3d1;
  }
  .detail-ai-wrap {
    margin-top: 1.25rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--line);
  }
  .detail-ai-h {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--text-3);
    font-weight: 600;
    margin: 0 0 0.65rem 0;
  }
  .section-label {
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: var(--text-3) !important;
    font-weight: 600 !important;
    margin: 0 0 var(--space-sm) 0 !important;
  }
  .sort-hint {
    font-size: 13px !important;
    color: var(--text-2) !important;
    margin: 0 0 var(--space-md) 0 !important;
    line-height: 1.55 !important;
  }
  .pill-tag {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--tag-gray-text);
    background: var(--tag-gray-bg);
    border: 1px solid var(--line);
    border-radius: var(--radius-pill);
    padding: 5px 11px;
    line-height: 1.2;
  }
  .fc-shell {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: var(--space-md) 1.25rem;
    margin-bottom: var(--space-md);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  }
  .fc-shell--tight { padding-bottom: 0.85rem !important; }
  .fc-shell-note {
    font-size: 12px !important;
    color: var(--text-3) !important;
    margin: 10px 0 0 0 !important;
    line-height: 1.45 !important;
  }
  .fc-kicker { font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-3); font-weight: 600; margin: 0 0 var(--space-sm) 0; }
  .fc-lede { font-size: 13px; color: var(--text-2); line-height: 1.55; margin: var(--space-md) 0 0 0; max-width: 44rem; }
  .fc-drivers { display: flex; flex-wrap: wrap; gap: var(--space-sm) 10px; margin-bottom: 0; }
  .fc-driver-pill {
    font-size: 12px; font-weight: 500;
    color: var(--text-2); background: #f1f5f9; border: 1px solid var(--line);
    border-radius: 999px; padding: 4px 10px;
  }
  .fc-decision-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: var(--space-md);
    margin-bottom: var(--space-lg);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
  }
  .fc-decision-card:hover {
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.07);
    border-color: #e2e8f0;
  }
  .fc-decision-card.fc-decision-card--selected {
    border-color: #93c5fd;
    background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
    box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.18);
  }
  .fc-card-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.4;
    letter-spacing: -0.02em;
    margin: 0 0 var(--space-md) 0;
  }
  .fc-divider {
    height: 1px;
    background: var(--line);
    margin: var(--space-md) 0;
    border: none;
  }
  .fc-quick-signal {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--space-md);
    margin-bottom: var(--space-md);
  }
  .fc-score-block { flex: 1; min-width: 140px; }
  .fc-score-num {
    font-size: 28px;
    font-weight: 600;
    color: #059669;
    letter-spacing: -0.03em;
    line-height: 1.1;
  }
  .fc-score-denom {
    font-size: 15px;
    font-weight: 500;
    color: var(--text-3);
  }
  .fc-conf-row {
    margin-top: var(--space-sm);
  }
  .fc-conf {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-2);
  }
  .fc-conf-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    background: #94a3b8;
  }
  .fc-conf-high .fc-conf-dot { background: #64748b; }
  .fc-conf-med .fc-conf-dot { background: #94a3b8; }
  .fc-conf-low .fc-conf-dot { background: #cbd5e1; }
  .fc-signal-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    justify-content: flex-end;
    max-width: 100%;
  }
  .fc-section-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    color: var(--text-3);
    margin: var(--space-md) 0 var(--space-sm) 0;
  }
  .fc-section-label:first-of-type { margin-top: 0; }
  .fc-bullet-list {
    margin: 0;
    padding-left: 1.15rem;
    font-size: 14px;
    line-height: 1.55;
    color: var(--text-2);
  }
  .fc-bullet-list li { margin-bottom: 8px; }
  .fc-action-highlight {
    font-size: 0.875rem;
    line-height: 1.55;
    font-weight: 500;
    color: var(--success-text);
    background: var(--success-bg);
    border: 1px solid var(--success-border);
    border-radius: var(--radius-card);
    padding: 12px 14px;
    margin-top: var(--space-sm);
  }
  .buyer-action-box {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    background: var(--success-bg);
    border: 1px solid var(--success-border);
    border-radius: var(--radius-card);
    padding: 12px 14px;
    margin-top: 2px;
  }
  .buyer-action-icon {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #10b981;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    margin-top: 1px;
  }
  .buyer-action-text {
    font-size: 0.875rem;
    line-height: 1.55;
    font-weight: 500;
    color: var(--success-text);
    margin: 0;
  }
  .fc-adv-note {
    font-size: 12px;
    color: var(--text-3);
    margin-top: var(--space-md);
    line-height: 1.5;
  }
  .outlook-box {
    margin-top: var(--space-md);
    padding-top: var(--space-md);
    border-top: 1px solid var(--line);
  }
  .outlook-k { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-3); font-weight: 600; margin-bottom: var(--space-sm); }
  .outlook-row { font-size: 13px; color: var(--text-2); line-height: 1.55; margin-bottom: 8px; }
  .pcard {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: var(--space-md);
    margin-bottom: var(--space-lg);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    transition: border-color 0.18s ease, box-shadow 0.18s ease;
  }
  .pcard:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
  }
  .pcard.pcard--selected {
    border-color: #93c5fd;
    background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
    box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.2);
  }
  .pcard-tags {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  .pcard-tags .badge-risk {
    font-size: 11px;
    padding: 5px 10px;
    font-weight: 600;
  }
  .pcard-title-row {
    margin-bottom: 10px;
  }
  .pcard-metrics {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.5rem 1.25rem;
    margin: 0 0 8px 0;
    font-size: 0.8125rem;
    color: var(--text-3);
  }
  .pcard-highlight-zone {
    font-size: 0.8125rem;
    color: var(--text-2);
    line-height: 1.45;
    padding: 10px 12px;
    background: #f8fafc;
    border-radius: 6px;
    border: 1px solid #f1f5f9;
    margin-top: 4px;
  }
  .pcard-highlight-zone ul { margin: 0; padding-left: 1.1rem; }
  .pcard-highlight-zone li { margin: 0 0 4px 0; }
  .panel-col-head {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--text-3);
    font-weight: 600;
    margin: 0 0 0.5rem 0;
  }
  .ts-inspection-subhead {
    margin: 0.35rem 0 1rem 0 !important;
    padding-bottom: 0.65rem !important;
    border-bottom: 1px solid #e2e8f0 !important;
  }
  /* Inner inspection content: cards sit on the column chrome; no forced min-height (column scrolls) */
  .detail-workspace {
    background: transparent;
    border: none;
    padding: 0;
    border-radius: 0;
    min-height: 0;
    box-sizing: border-box;
    margin-top: 0;
  }
  section[data-testid="stMain"] [data-testid="stVerticalBlock"]:has(.ts-inspect-drawer-marker) .detail-workspace .dw-card {
    background: #ffffff !important;
    border-color: #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
  }
  .dw-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: var(--space-md);
    margin-top: var(--space-md);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  }
  .dw-card:first-of-type { margin-top: 0; }
  .dw-overview .detail-title { margin-top: 0; }
  .detail-workspace .detail-kicker { margin-bottom: 0.5rem; }
  .detail-workspace .detail-title {
    font-size: 1.125rem;
    line-height: 1.35;
    margin-bottom: 0.5rem;
  }
  .dw-section {
    margin-top: 0;
    padding-top: 0;
    border-top: none;
  }
  .dw-h {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3);
    font-weight: 600;
    margin: 0 0 0.5rem 0;
  }
  .dw-h--muted {
    font-size: 0.62rem;
    color: #94a3b8;
    letter-spacing: 0.12em;
  }
  .dw-tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }
  .dw-ul {
    margin: 0;
    padding-left: 1.1rem;
    font-size: 0.8125rem;
    color: var(--text-2);
    line-height: 1.55;
  }
  .dw-ul li { margin-bottom: 0.35rem; }
  .dw-highlights {
    margin: 0;
    padding-left: 1.1rem;
    font-size: 0.78rem;
    color: var(--text-2);
    line-height: 1.5;
  }
  .dw-highlights li { margin-bottom: 0.3rem; }
  .pcard-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 0.65rem;
  }
  .pcard .ptitle {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.35;
    letter-spacing: -0.02em;
  }
  .pcard-stats {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.5rem 1.25rem;
    margin: 0.5rem 0 0.35rem 0;
    font-size: 13px;
    color: var(--text-3);
  }
  .pcard-price {
    font-size: 17px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.02em;
  }
  .pcard-rating { font-weight: 500; color: var(--text-2); font-size: 13px; }
  .pcard-opp {
    font-size: 0.75rem;
    color: var(--text-3);
    margin-top: 0.35rem;
  }
  .pcard-actions {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
  }
  .tag-query {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--tag-gray-text);
    background: var(--tag-gray-bg);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.18rem 0.45rem;
    margin-bottom: 0;
  }
  .pcard-bullets {
    font-size: 0.8125rem;
    color: var(--text-2);
    margin: 0.65rem 0 0 1rem;
    padding: 0;
    line-height: 1.5;
  }
  .pcard-bullets li { margin-bottom: 0.25rem; }
  .muted-asin { color: var(--text-3); font-size: 0.68rem; font-family: ui-monospace, monospace; }
  .amo-link {
    display: inline-block;
    margin-top: 0.5rem;
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--text) !important;
    text-decoration: none !important;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.35rem 0.75rem;
    background: var(--surface);
  }
  .amo-link:hover {
    background: var(--accent-soft);
    border-color: var(--line-strong);
  }
  hr.sep {
    border: none;
    border-top: 1px solid var(--line);
    margin: var(--space-xl) 0 var(--space-lg) 0;
  }
  .stButton > button[kind="primary"] {
    border-radius: var(--radius-card) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    background: var(--primary) !important;
    border: 1px solid var(--primary) !important;
    color: #ffffff !important;
    box-shadow: none !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: var(--primary-hover) !important;
    border-color: var(--primary-hover) !important;
  }
  .stButton > button[kind="secondary"] {
    border-radius: var(--radius-card) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    background: var(--surface) !important;
    border: 1px solid var(--line-strong) !important;
    color: var(--text) !important;
    box-shadow: none !important;
  }
  .stButton > button[kind="secondary"]:hover {
    border-color: #94a3b8 !important;
    background: #f8fafc !important;
  }
  a.ts-btn-primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    padding: 0.55rem 1.1rem;
    border-radius: var(--radius-card);
    font-weight: 600;
    font-size: 0.875rem;
    background: var(--primary);
    color: #ffffff !important;
    text-decoration: none !important;
    border: 1px solid var(--primary);
    transition: background 0.15s ease, border-color 0.15s ease;
  }
  a.ts-btn-primary:hover {
    background: var(--primary-hover);
    border-color: var(--primary-hover);
    color: #ffffff !important;
  }
  a.ts-btn-primary.ts-btn-block {
    display: flex;
    width: 100%;
  }
  [data-testid="stLinkButton"] a {
    border-radius: var(--radius-card) !important;
    font-weight: 500 !important;
  }
  [data-testid="stCaptionContainer"] p,
  .stCaption {
    color: var(--text-3) !important;
  }
  /* Buyer Decision Assistant (dedicated page) */
  .copilot-hero {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1.35rem 1.4rem;
    margin: 1.25rem 0 1rem 0;
    box-shadow: none;
  }
  .copilot-hero-kicker {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--text-3);
    font-weight: 600;
    margin: 0 0 0.35rem 0;
  }
  .copilot-hero-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.02em;
    margin: 0 0 0.35rem 0;
    line-height: 1.25;
  }
  .copilot-hero-sub {
    font-size: 0.8125rem;
    color: var(--text-2);
    margin: 0;
    line-height: 1.55;
    max-width: 42rem;
  }
  .copilot-result-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    margin-top: 0.75rem;
    box-shadow: none;
  }
  .copilot-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 0.5rem;
    align-items: center;
    margin-bottom: 0.85rem;
  }
  .copilot-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    border-radius: 4px;
    padding: 0.25rem 0.55rem;
    border: 1px solid var(--line);
  }
  .copilot-badge.rec-ok { background: #f7fdf9; color: #14532d; border-color: #bbf7d0; }
  .copilot-badge.rec-review { background: #fafafa; color: #404040; border-color: #e5e5e5; }
  .copilot-badge.rec-manual { background: #fffbeb; color: #92400e; border-color: #fde68a; }
  .copilot-badge.rec-no { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
  .copilot-badge.conf-low { background: #fafafa; color: #525252; border-color: #e5e5e5; }
  .copilot-badge.conf-med { background: #f5f5f5; color: #404040; border-color: #d4d4d4; }
  .copilot-badge.conf-high { background: #f5f5f5; color: #171717; border-color: #a3a3a3; }
  .copilot-section-title {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3);
    font-weight: 600;
    margin: 0.85rem 0 0.35rem 0;
  }
  .copilot-section-title:first-of-type { margin-top: 0; }
  .copilot-summary {
    font-size: 0.875rem;
    color: var(--text);
    line-height: 1.55;
    margin: 0 0 0.35rem 0;
  }
  .copilot-list {
    margin: 0;
    padding-left: 1.1rem;
    font-size: 0.8125rem;
    color: var(--text-2);
    line-height: 1.5;
  }
  .copilot-list li { margin-bottom: 0.3rem; }
  [data-testid="stExpander"] details {
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
    background: var(--surface) !important;
    padding: 2px 4px !important;
  }
  [data-testid="stExpander"] summary {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text-2) !important;
  }
  .main .block-container {
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
  }
  /* Gutters between main layout columns (dashboard row) */
  .block-container > div > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
    gap: 1.35rem !important;
    column-gap: 1.35rem !important;
  }
  /* Filters column (main row — two-column dashboard) */
  section[data-testid="stMain"] .block-container > div > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
    position: sticky !important;
    top: 0.75rem !important;
    align-self: flex-start !important;
    max-height: calc(100vh - 1.5rem) !important;
    overflow-y: auto !important;
    background: #ffffff !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
    padding: 0.35rem 0.65rem 0.85rem 0.65rem !important;
    box-sizing: border-box !important;
  }
  /* Center column only (main dashboard row — not nested card button rows) */
  section[data-testid="stMain"] .block-container > div > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
    max-height: calc(100vh - 4.5rem) !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding-right: 0.5rem !important;
    box-sizing: border-box !important;
  }
  /* Right-side inspection drawer: fixed overlay without grabbing the whole main stack.
     (1) Sibling after the main filter|content row — works when DOM is flat.
     (2) stVerticalBlock that contains the marker and does NOT contain any stHorizontalBlock
         under it. The main app wrapper contains the dashboard row (often nested), so it
         must not match; the drawer stack is a sibling branch and has no row layouts. */
  section[data-testid="stMain"]
    div[data-testid="stHorizontalBlock"]
    ~ div[data-testid="stVerticalBlock"]:has(.ts-inspect-drawer-marker),
  section[data-testid="stMain"]
    div[data-testid="stVerticalBlock"]:has(.ts-inspect-drawer-marker):not(:has(div[data-testid="stHorizontalBlock"])) {
    position: fixed !important;
    top: 0 !important;
    right: 0 !important;
    left: auto !important;
    width: min(440px, calc(100vw - 1rem)) !important;
    min-width: 280px !important;
    max-width: 480px !important;
    height: 100vh !important;
    max-height: 100vh !important;
    margin: 0 !important;
    padding: 1rem 1.1rem 1.5rem !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    -webkit-overflow-scrolling: touch !important;
    overscroll-behavior: contain !important;
    z-index: 100050 !important;
    background: #ffffff !important;
    border-left: 3px solid #0052cc !important;
    box-shadow: -12px 0 40px rgba(9, 30, 66, 0.2) !important;
    box-sizing: border-box !important;
    writing-mode: horizontal-tb !important;
    text-orientation: mixed !important;
    word-break: normal !important;
    overflow-wrap: break-word !important;
  }
  .ts-inspect-placeholder {
    font-size: 0.8125rem !important;
    color: var(--text-3) !important;
    line-height: 1.55 !important;
    margin: 0.35rem 0 0 0 !important;
    padding: 0.25rem 0.15rem 0 0 !important;
  }
  .ts-inspect-kicker {
    font-size: 0.62rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: #64748b !important;
    font-weight: 600 !important;
    margin: 0 0 0.5rem 0 !important;
  }
  .fc-compact-summary {
    font-size: 12px !important;
    color: var(--text-2) !important;
    line-height: 1.45 !important;
    margin: 0.35rem 0 0 0 !important;
  }
  .fc-compact-meta {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    align-items: center !important;
    margin-top: 6px !important;
  }
  .fc-compact-tags {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    margin-top: 6px !important;
  }
  /* Bordered scan cards (st.container(border=True)) — Details sits inside box, bottom-right */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--line) !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    padding: 12px 14px 10px !important;
    margin-bottom: 0.75rem !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ts-scan-inner--selected) {
    border-color: #4c9aff !important;
    box-shadow: 0 0 0 1px rgba(0, 82, 204, 0.25) !important;
  }
  .ts-scan-inner { margin: 0; }
  .ts-scan-with-rank {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: 12px;
  }
  .ts-scan-rank {
    flex-shrink: 0;
    min-width: 2.35rem;
    font-size: 15px;
    font-weight: 700;
    color: var(--primary);
    letter-spacing: -0.02em;
    line-height: 1.35;
    padding-top: 1px;
  }
  .ts-scan-with-rank-body {
    flex: 1;
    min-width: 0;
  }
  .ts-scan-title-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin: 0 0 10px 0;
  }
  .ts-scan-title-row .ts-scan-title-full {
    margin: 0;
    flex: 1;
    min-width: 0;
  }
  .ts-scan-title-row .badge-risk {
    font-size: 11px !important;
    font-weight: 700 !important;
    padding: 4px 10px !important;
    border-radius: 6px !important;
    line-height: 1.2 !important;
    letter-spacing: 0.02em !important;
    margin-top: 1px;
    box-shadow: none !important;
  }
  .ts-scan-title-row .badge-risk + .badge-risk {
    margin-left: 8px;
  }
  .ts-scan-title-full {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.35;
    letter-spacing: -0.02em;
    margin: 0 0 10px 0;
  }
  .ts-scan-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin: 0 0 6px 0;
  }
  .ts-scan-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.35;
    letter-spacing: -0.02em;
    margin: 0;
    flex: 1;
    min-width: 0;
  }
  .ts-scan-score-main {
    font-size: 18px;
    font-weight: 700;
    color: var(--primary);
    letter-spacing: -0.03em;
    line-height: 1.2;
    flex-shrink: 0;
  }
  .ts-scan-score-block {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    margin: 0 0 8px 0;
  }
  .ts-scan-score-block--primary { margin-bottom: 6px; }
  .ts-scan-score-block--secondary { margin-bottom: 8px; }
  .ts-scan-lbl {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-3);
  }
  .ts-scan-val { line-height: 1.15; letter-spacing: -0.03em; }
  .ts-scan-val--forecast {
    font-size: 22px;
    font-weight: 700;
    color: var(--primary);
  }
  .ts-scan-val--current {
    font-size: 16px;
    font-weight: 600;
    color: #42526e;
  }
  .ts-scan-line {
    font-size: 12px;
    font-weight: 600;
    color: #42526e;
    margin: 0 0 8px 0;
    letter-spacing: -0.01em;
  }
  .ts-scan-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin: 0 0 8px 0;
  }
  .ts-scan-tags .pill-tag {
    font-size: 0.62rem !important;
    padding: 3px 8px !important;
    font-weight: 500 !important;
  }
  .pill-tag.pill-tag--query {
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-size: 0.6rem !important;
  }
  .ts-scan-desc {
    font-size: 12px;
    color: var(--text-3);
    line-height: 1.45;
    margin: 0 0 4px 0;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
    align-items: flex-end !important;
    gap: 0.5rem !important;
    margin-top: 2px !important;
    margin-bottom: 0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
    min-height: 0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] button {
    font-size: 0.8125rem !important;
    min-height: 2.1rem !important;
  }
  [data-testid="stToolbar"],
  header[data-testid="stToolbar"] {
    z-index: 100095 !important;
    visibility: visible !important;
  }
</style>
"""


def render_sidebar_menu_button() -> None:
    """Always-visible ☰ (GPT-style) that opens the collapsed filters sidebar via the parent frame."""
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    # Valid JS in parent document; json.dumps safely escapes for the HTML attribute.
    _js = (
        "try{var d=window.parent.document;"
        "var e=d.querySelector(" + json.dumps('[data-testid="stExpandSidebarButton"]') + ");"
        "if(e){e.click();return;}"
        "e=d.querySelector(" + json.dumps('button[aria-label="Open sidebar"]') + ");"
        "if(e){e.click();return;}"
        "var h=d.querySelector(" + json.dumps('[data-testid="stHeader"]') + ");"
        "if(h){var b=h.querySelector('button');if(b)b.click();}"
        "}catch(x){}"
    )
    components.html(
        f"""
<div style="position:fixed;top:1rem;left:0.85rem;z-index:10060;pointer-events:auto;">
  <button type="button" title="Open filters sidebar" aria-label="Open sidebar"
    onclick={json.dumps(_js)}
    style="background:#ffffff;border:1px solid #e8e8e8;border-radius:8px;width:40px;height:40px;cursor:pointer;
    color:#171717;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 2px rgba(0,0,0,0.06);
    padding:0;margin:0;">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  </button>
</div>
        """,
        height=48,
    )


def render_header():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        """
<div class="ts-page-hero">
  <h1 class="ts-hero-title">SipScope</h1>
  <p class="ts-hero-tagline">Retail buying signals</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(df: pd.DataFrame):
    n = len(df)
    avg_r = df["rating"].mean() if n else 0.0
    avg_p = df["price_num"].mean() if n and df["price_num"].notna().any() else 0.0
    max_rev = int(df["review_count"].max()) if n else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("SKUs in view", f"{n:,}")
    with c2:
        st.metric("Avg. rating", f"{avg_r:.2f}" if n else "—")
    with c3:
        st.metric("Avg. price", f"${avg_p:.2f}" if n and pd.notna(avg_p) else "—")
    with c4:
        st.metric("Max reviews", f"{max_rev:,}" if n else "—")


def _fc_confidence_row_html(conf_raw: str) -> str:
    c = (conf_raw or "").strip().lower()
    tier = "fc-conf-low"
    if c == "high":
        tier = "fc-conf-high"
    elif c == "medium":
        tier = "fc-conf-med"
    label = html.escape((conf_raw or "—").strip())
    return (
        f'<div class="fc-conf-row"><span class="fc-conf {tier}">'
        f'<span class="fc-conf-dot" aria-hidden="true"></span>{label}</span></div>'
    )


def _fc_why_now_bullets(fr: dict) -> list[str]:
    lines: list[str] = []
    for r in (fr.get("future_reasons") or [])[:6]:
        s = str(r).strip()
        if not s:
            continue
        if len(s) > 180:
            s = s[:177] + "…"
        lines.append(s)
    return lines or ["Limited calendar overlap in the next 30 days — treat as exploratory."]


def _scan_card_container():
    """Product row wrapper so the Details button sits inside the same bordered box."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def render_forecast_intro(upcoming_events: list) -> None:
    """Section title + driver shell (full width)."""
    st.markdown(
        """
<div class="section-head">
  <p class="section-head-k">Forecast</p>
  <p class="section-head-t">30-Day Opportunity Forecast</p>
  <p class="section-head-s">Calendar rules + listing text → forward-looking <strong>signals</strong>. Not a demand forecast.</p>
</div>
        """,
        unsafe_allow_html=True,
    )
    driver_html = ""
    for ev in upcoming_events[:8]:
        nm = html.escape(str(ev.get("name") or ""))
        driver_html += f'<span class="fc-driver-pill">{nm}</span>'
    if not driver_html:
        driver_html = '<span class="fc-driver-pill">No drivers in window (rules)</span>'

    st.markdown(
        f"""
<div class="fc-shell fc-shell--tight">
  <p class="fc-kicker">Next 30 days · active drivers</p>
  <div class="fc-drivers">{driver_html}</div>
  <p class="fc-shell-note">Ranked by forward opportunity score — open <strong>Details</strong> for full analysis.</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_forecast_cards_only(
    top_fc: pd.DataFrame,
    fdf: pd.DataFrame,
    forecast_by_asin: dict[str, dict] | None,
    fp_key: str,
) -> None:
    """Compact forecast rows — open the right panel only via Details."""
    if top_fc.empty:
        st.caption("No products to score under current filters.")
        return

    fmap = forecast_by_asin or {}
    sel = st.session_state.get(SELECTED_PRODUCT_KEY)
    detail_open = bool(st.session_state.get(DETAIL_OPEN_KEY))

    def _pick_fc(idx_val: int) -> None:
        r = top_fc.iloc[idx_val]
        resolved = fdf.iloc[_fdf_iloc_for_row(fdf, r)]
        st.session_state[SELECTED_PRODUCT_KEY] = row_to_selected_product(resolved)
        st.session_state[DETAIL_OPEN_KEY] = True

    for idx, (_, row) in enumerate(top_fc.iterrows()):
        aid = str(row.get("asin") or "")
        fr = fmap.get(aid) or {}
        title_raw = str(row.get("amazon_title") or "—")
        title = html.escape(title_raw[:82] + ("…" if len(title_raw) > 82 else ""))
        fs = float(row.get("future_opportunity_score") or 0)
        cur_fit = float(row.get("opportunity_score") or 0)
        flab = html.escape(str(row.get("forecast_label") or "—"))
        badges = row.get("forecast_badges") or []
        bl = badges if isinstance(badges, list) else []
        tag_pills = "".join(
            f'<span class="pill-tag">{html.escape(str(b))}</span>' for b in bl[:3]
        )
        if flab and flab != "—":
            tag_pills += f'<span class="pill-tag">{flab}</span>'

        row_iloc = _fdf_iloc_for_row(fdf, row)
        cur = fdf.iloc[row_iloc]
        summary = html.escape(_one_line_summary(cur, fr))
        if len(summary) > 118:
            summary = summary[:115] + "…"
        is_sel = detail_open and isinstance(sel, dict) and _same_listing_row(cur, sel)
        sel_cls = " ts-scan-inner--selected" if is_sel else ""
        fs_str = html.escape(f"{fs:.1f}")
        cur_str = html.escape(f"{cur_fit:.1f}")
        rank_n = idx + 1
        rank_label = html.escape(f"#{rank_n}")
        risk_tier = str(cur.get("risk_level") or "").strip() or estimate_risk_level(cur)
        rb = risk_badge_class(risk_tier)
        risk_esc = html.escape(risk_tier)
        risk_badge_html = f'<span class="{rb}">{risk_esc}</span>'

        card_html = f"""
<div class="ts-scan-inner ts-scan-inner--forecast{sel_cls}">
  <div class="ts-scan-with-rank">
    <span class="ts-scan-rank" aria-label="Rank {rank_n}">{rank_label}</span>
    <div class="ts-scan-with-rank-body">
      <div class="ts-scan-title-row">
        <div class="ts-scan-title-full">{title}</div>
        {risk_badge_html}
      </div>
      <div class="ts-scan-score-block ts-scan-score-block--primary">
        <span class="ts-scan-lbl">30-Day Forecast</span>
        <span class="ts-scan-val ts-scan-val--forecast">{fs_str}</span>
      </div>
      <div class="ts-scan-score-block ts-scan-score-block--secondary">
        <span class="ts-scan-lbl">Current Score</span>
        <span class="ts-scan-val ts-scan-val--current">{cur_str}</span>
      </div>
      <div class="ts-scan-tags">{tag_pills}</div>
      <p class="ts-scan-desc">{summary}</p>
    </div>
  </div>
</div>
"""
        with _scan_card_container():
            st.markdown(card_html, unsafe_allow_html=True)
            _pad, _btn = st.columns([3, 1])
            with _btn:
                st.button(
                    "Details",
                    key=f"fc_det_{fp_key}_{idx}",
                    on_click=_pick_fc,
                    args=(idx,),
                    type="primary" if is_sel else "secondary",
                    use_container_width=True,
                )


def render_persistent_detail_panel(
    fdf: pd.DataFrame,
    forecast_by_asin: dict[str, dict] | None,
) -> None:
    """Detail UI in the third main column — wide enough for normal text wrapping."""
    st.button(
        "← Back to results",
        key="ts_back_to_results",
        on_click=_close_detail_panel,
        use_container_width=True,
    )
    if fdf.empty:
        st.caption("No products in view — adjust filters.")
        return

    sp = st.session_state.get(SELECTED_PRODUCT_KEY)
    row: pd.Series | None = None
    if isinstance(sp, dict) and sp:
        for i in range(len(fdf)):
            if _same_listing_row(fdf.iloc[i], sp):
                row = fdf.iloc[i]
                break
    if row is None:
        st.caption("Select a product from Forecast or All results.")
        return

    aid = str(row.get("asin") or "")
    fr = (forecast_by_asin or {}).get(aid) if forecast_by_asin else None

    render_detail_panel(row, forecast=fr, panel_mode=True)


def format_rec_radio_label(asin: str, top5: pd.DataFrame) -> str:
    rows = top5.reset_index(drop=True)
    try:
        idx = rows["asin"].tolist().index(asin) + 1
    except ValueError:
        idx = 1
    row = rows[rows["asin"] == asin].iloc[0]
    t = str(row.get("amazon_title") or "")
    short = (t[:44] + "…") if len(t) > 46 else t
    sc = float(row.get("opportunity_score") or 0)
    risk = str(row.get("risk_level") or estimate_risk_level(row))
    return f"#{idx}  {short}\n    {sc:.0f} fit · {risk}"


def _gpt_buyer_session_keys(row: pd.Series) -> tuple[str, str, str]:
    """Session state keys for cached GPT analysis per listing (detail drawer)."""
    raw = str(row.get("asin") or "").strip() or hashlib.sha256(
        f"{row.get('url') or ''}|{row.get('query') or ''}".encode()
    ).hexdigest()[:16]
    safe = re.sub(r"[^0-9A-Za-z]", "_", raw)[:48]
    pfx = f"ts_gpt_buyer_{safe}"
    return f"{pfx}_result", f"{pfx}_err", f"{pfx}_btn"


def _render_gpt_buyer_section(row: pd.Series) -> None:
    """OpenAI buyer screening in the detail drawer (same engine as Buyer Decision Assistant)."""
    k_res, k_err, k_btn = _gpt_buyer_session_keys(row)
    with st.expander("GPT buyer analysis", expanded=False):
        st.caption(
            "Same screening model as **Buyer Decision Assistant** — not medical, legal, or regulatory advice."
        )
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            st.info("Set **OPENAI_API_KEY** in `.env` to run analysis.")
            return
        if st.button("Run GPT analysis", key=k_btn, type="secondary", use_container_width=True):
            st.session_state[k_err] = None
            st.session_state[k_res] = None
            try:
                product_name, product_info = format_product_context_for_analysis(row)
                st.session_state[k_res] = analyze_product(product_name, product_info)
            except Exception as e:
                st.session_state[k_err] = str(e)
            st.rerun()
        err = st.session_state.get(k_err)
        if err:
            st.error(html.escape(str(err)))
        res = st.session_state.get(k_res)
        if isinstance(res, dict) and res:
            render_copilot_gpt_result(res, show_heading=False, use_chat_message=False)


def _render_detail_workspace(row: pd.Series, forecast: dict | None) -> None:
    """Right-column inspection layout for All results (master–detail; no modal)."""
    fr = forecast
    title = html.escape(str(row.get("amazon_title") or "—"))
    q = html.escape(str(row.get("query") or "—"))
    price = html.escape(price_display(row))
    url = str(row.get("url") or "")
    score = float(row.get("opportunity_score") or 0)
    rating = row.get("rating", "—")
    rev = int(row.get("review_count") or 0)
    rank = int(row.get("search_result_rank_used") or 0)
    asin_esc = html.escape(str(row.get("asin") or "—"))
    risk = str(row.get("risk_level") or estimate_risk_level(row))
    rb = risk_badge_class(risk)
    risk_esc = html.escape(risk)

    bullets = row.get("bullets") or []
    blist = bullets if isinstance(bullets, list) else []
    why_li = "".join(f"<li>{html.escape(str(b)[:400])}</li>" for b in blist[:8])

    hl_lines: list[str] = []
    if fr:
        hl_lines.extend(_fc_why_now_bullets(fr)[:5])
        for t in (fr.get("derived_tags") or [])[:5]:
            s = str(t).strip()
            if s and s not in hl_lines:
                hl_lines.append(s)
    if not hl_lines and blist:
        for b in blist[:5]:
            s = str(b).strip()
            if len(s) > 110:
                s = s[:107] + "…"
            if s:
                hl_lines.append(s)
    hi_li = "".join(f"<li>{html.escape(h)}</li>" for h in hl_lines[:8])

    buyer_act = str(fr.get("buyer_action") or "").strip() if fr else ""

    # Single-line / no leading-indent HTML — indented lines are rendered as Markdown code blocks.
    _pair_parts: list[str] = ['<div class="dw-score-pair">']
    if fr:
        fs_disp = float(fr.get("future_opportunity_score") or 0)
        _pair_parts.append(
            f'<div class="dw-score-row dw-score-row--forecast"><span class="dw-sl">30-Day Forecast</span>'
            f'<span class="dw-sv dw-sv-forecast">{fs_disp:.1f}</span></div>'
        )
    _pair_parts.append(
        f'<div class="dw-score-row dw-score-row--current"><span class="dw-sl">Current Score</span>'
        f'<span class="dw-sv dw-sv-current">{score:.1f}</span></div></div>'
    )
    score_pair_html = "".join(_pair_parts)

    outlook_html = ""
    if fr:
        evs = fr.get("relevant_upcoming_events") or []
        ev_line = ", ".join(evs) if evs else "—"
        ev_line_e = html.escape(ev_line)
        fs = float(fr.get("future_opportunity_score") or 0)
        flab = html.escape(str(fr.get("forecast_label") or "—"))
        conf = html.escape(str(fr.get("forecast_confidence") or "—"))
        reasons = fr.get("future_reasons") or []
        reason_txt = html.escape(reasons[0]) if reasons else "—"
        badges = fr.get("event_badges") or []
        bh = "".join(f'<span class="pill-tag">{html.escape(str(b))}</span>' for b in badges[:5])
        outlook_html = f"""
  <div class="dw-card">
    <div class="dw-h">30-Day outlook</div>
    <ul class="dw-ul">
      <li><strong>30-Day Forecast</strong> {fs:.1f} · <strong>Label</strong> {flab} · <strong>Confidence</strong> {conf}</li>
      <li><strong>Drivers</strong> {ev_line_e}</li>
      <li>{reason_txt}</li>
    </ul>
    <div class="dw-tag-row">{bh}</div>
  </div>
"""
    else:
        outlook_html = """
  <div class="dw-card">
    <div class="dw-h">30-Day outlook</div>
    <p class="dw-muted">No forecast data for this listing under current rules.</p>
  </div>
"""

    why_block = ""
    if why_li.strip():
        why_block = f"""
  <div class="dw-card">
    <div class="dw-h">Why this product</div>
    <ul class="dw-ul">{why_li}</ul>
  </div>
"""

    buyer_block = ""
    if buyer_act:
        buyer_block = f"""
  <div class="dw-card">
    <div class="dw-h">Buyer action</div>
    <div class="buyer-action-box">
      <span class="buyer-action-icon" aria-hidden="true">✓</span>
      <p class="buyer-action-text">{html.escape(buyer_act)}</p>
    </div>
  </div>
"""

    hi_block = ""
    if hi_li.strip():
        hi_block = f"""
  <div class="dw-card">
    <div class="dw-h">Highlights</div>
    <ul class="dw-highlights">{hi_li}</ul>
  </div>
"""

    shelf_s, ben_s, ing_s, region_s = _row_listing_facts(row)

    def _listing_extra_row(label: str, text: str) -> str:
        lab_e = html.escape(label)
        if text.strip():
            return (
                f'<div class="extra-block"><div class="extra-label">{lab_e}</div>'
                f'<p class="extra-body">{html.escape(text)}</p></div>'
            )
        return (
            f'<div class="extra-block"><div class="extra-label">{lab_e}</div>'
            f'<p class="extra-body muted">Not listed</p></div>'
        )

    listing_facts_html = f"""
  <div class="dw-card">
    <div class="dw-h">Shelf life, benefits, ingredients & origin</div>
    <div class="detail-extras dw-listing-detail-extras">
      {_listing_extra_row("Product shelf life", shelf_s)}
      {_listing_extra_row("Product benefits", ben_s)}
      {_listing_extra_row("Special ingredients", ing_s)}
      {_listing_extra_row("Region of origin", region_s)}
    </div>
  </div>
"""

    st.markdown(
        f"""
<div class="detail-workspace">
  <div class="dw-card dw-overview">
    <div class="detail-title">{title}</div>
    {score_pair_html}
    <div class="detail-price">{price}</div>
    <div class="detail-meta-row">
      <span class="{rb}">{risk_esc}</span>
      <span class="tag-pill">{q}</span>
    </div>
    <div class="detail-grid detail-grid--panel">
      <div><span class="label">Rating</span><span class="val">{rating} ★</span></div>
      <div><span class="label">Reviews</span><span class="val">{rev:,}</span></div>
      <div><span class="label">Search rank</span><span class="val">#{rank}</span></div>
    </div>
    <div class="detail-asin">ASIN {asin_esc}</div>
  </div>
{listing_facts_html}
{outlook_html}
{why_block}
{buyer_block}
{hi_block}
</div>
        """,
        unsafe_allow_html=True,
    )

    if url:
        st.markdown(
            f'<a class="ts-btn-primary ts-btn-block" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">View on Amazon ↗</a>',
            unsafe_allow_html=True,
        )

    _render_gpt_buyer_section(row)


def render_detail_panel(
    row: pd.Series,
    forecast: dict | None = None,
    *,
    panel_mode: bool = False,
) -> None:
    if panel_mode:
        _render_detail_workspace(row, forecast)
        return

    title = html.escape(str(row.get("amazon_title") or "—"))
    q = html.escape(str(row.get("query") or "—"))
    price = html.escape(price_display(row))
    url = str(row.get("url") or "")
    score = float(row.get("opportunity_score") or 0)
    rating = row.get("rating", "—")
    rev = int(row.get("review_count") or 0)
    rank = int(row.get("search_result_rank_used") or 0)
    asin_esc = html.escape(str(row.get("asin") or "—"))
    risk = str(row.get("risk_level") or estimate_risk_level(row))
    rb = risk_badge_class(risk)
    risk_esc = html.escape(risk)

    bullets = row.get("bullets") or []
    b_show = bullets[:3] if isinstance(bullets, list) else []
    li = "".join(f"<li>{html.escape(str(b)[:320])}</li>" for b in b_show)

    shelf_s, ben_s, ing_s, region_s = _row_listing_facts(row)
    shelf_html = (
        f'<p class="extra-body">{html.escape(shelf_s)}</p>'
        if shelf_s.strip()
        else '<p class="extra-body muted">Not listed</p>'
    )
    ben_html = (
        f'<p class="extra-body">{html.escape(ben_s)}</p>'
        if ben_s.strip()
        else '<p class="extra-body muted">Not listed</p>'
    )
    ing_html = (
        f'<p class="extra-body">{html.escape(ing_s)}</p>'
        if ing_s.strip()
        else '<p class="extra-body muted">Not listed</p>'
    )
    region_html = (
        f'<p class="extra-body">{html.escape(region_s)}</p>'
        if region_s.strip()
        else '<p class="extra-body muted">Not listed</p>'
    )

    st.markdown(
        f"""
<div class="detail-shell">
  <div class="detail-kicker">Detail</div>
  <div class="detail-meta-row">
    <span class="{rb}">{risk_esc}</span>
    <span class="tag-pill">{q}</span>
    <span class="score-pill-lg">Current Score {score:.1f}</span>
  </div>
  <div class="detail-title">{title}</div>
  <div class="detail-price">{price}</div>
  <div class="detail-grid">
    <div><span class="label">Rating</span><span class="val">{rating} ★</span></div>
    <div><span class="label">Reviews</span><span class="val">{rev:,}</span></div>
    <div><span class="label">Search rank</span><span class="val">#{rank}</span></div>
  </div>
  <div class="detail-extras">
    <div class="extra-block">
      <div class="extra-label">Product shelf life</div>
      {shelf_html}
    </div>
    <div class="extra-block">
      <div class="extra-label">Product benefits</div>
      {ben_html}
    </div>
    <div class="extra-block">
      <div class="extra-label">Special ingredients</div>
      {ing_html}
    </div>
    <div class="extra-block">
      <div class="extra-label">Region of origin</div>
      {region_html}
    </div>
  </div>
  <div style="font-size:0.62rem;color:#737373;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.35rem;margin-top:0.85rem;font-weight:600">Highlights</div>
  <ul class="detail-bullets">{li}</ul>
  <div class="detail-asin">ASIN {asin_esc}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    if url:
        st.markdown(
            f'<a class="ts-btn-primary ts-btn-block" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">View on Amazon ↗</a>',
            unsafe_allow_html=True,
        )

    _render_gpt_buyer_section(row)

    if forecast:
        evs = forecast.get("relevant_upcoming_events") or []
        ev_line = ", ".join(evs) if evs else "—"
        ev_line_e = html.escape(ev_line)
        fs = float(forecast.get("future_opportunity_score") or 0)
        flab = html.escape(str(forecast.get("forecast_label") or "—"))
        conf = html.escape(str(forecast.get("forecast_confidence") or "—"))
        reasons = forecast.get("future_reasons") or []
        reason_txt = reasons[0] if reasons else ""
        act = html.escape(str(forecast.get("buyer_action") or ""))
        badges = forecast.get("event_badges") or []
        bh = "".join(f'<span class="pill-tag">{html.escape(str(b))}</span>' for b in badges[:5])
        st.markdown(
            f"""
<div class="outlook-box">
  <div class="outlook-k">30-Day outlook</div>
  <div class="outlook-row"><strong>30-Day Forecast:</strong> {fs:.1f} · <strong>Label:</strong> {flab} · <strong>Confidence:</strong> {conf}</div>
  <div class="outlook-row"><strong>Upcoming drivers:</strong> {ev_line_e}</div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin:0.5rem 0">{bh}</div>
  <div class="outlook-row">{html.escape(reason_txt)}</div>
  <div class="outlook-row"><strong>Suggested action:</strong> {act}</div>
</div>
            """,
            unsafe_allow_html=True,
        )


def render_recommended_block(
    top5: pd.DataFrame,
    fdf: pd.DataFrame,
    fp_key: str,
    forecast_by_asin: dict[str, dict] | None,
) -> None:
    """Compact priority queue — Details opens the right panel."""
    st.markdown(
        """
<div class="section-head">
  <p class="section-head-k">Workflow</p>
  <p class="section-head-t">Priority Buying Queue</p>
  <p class="section-head-s">Top five SKUs for your filters and <strong>sort order</strong>. Use <strong>Details</strong> to inspect on the right.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    if top5.empty:
        st.caption("No products match the current filters.")
        return

    fmap = forecast_by_asin or {}
    sel = st.session_state.get(SELECTED_PRODUCT_KEY)
    detail_open = bool(st.session_state.get(DETAIL_OPEN_KEY))

    def _pick_pq(idx_val: int) -> None:
        r = top5.iloc[idx_val]
        resolved = fdf.iloc[_fdf_iloc_for_row(fdf, r)]
        st.session_state[SELECTED_PRODUCT_KEY] = row_to_selected_product(resolved)
        st.session_state[DETAIL_OPEN_KEY] = True

    for i in range(len(top5)):
        row = top5.iloc[i]
        aid = str(row.get("asin") or "")
        fr = fmap.get(aid) or {}
        title_raw = str(row.get("amazon_title") or "—")
        title = html.escape(title_raw[:82] + ("…" if len(title_raw) > 82 else ""))
        sc = float(row.get("opportunity_score") or 0)
        dt = fr.get("derived_tags") if fr else None
        dt_list = dt if isinstance(dt, list) else []
        tag_bits = "".join(
            f'<span class="pill-tag">{html.escape(str(t))}</span>' for t in dt_list[:2]
        )
        summary = html.escape(_one_line_summary(row, fr))
        if len(summary) > 118:
            summary = summary[:115] + "…"
        cur = fdf.iloc[_fdf_iloc_for_row(fdf, row)]
        is_sel = detail_open and isinstance(sel, dict) and _same_listing_row(cur, sel)
        sel_cls = " ts-scan-inner--selected" if is_sel else ""
        score_big = html.escape(f"{sc:.1f}")
        rank_n = i + 1
        rank_label = html.escape(f"#{rank_n}")
        risk_tier = str(cur.get("risk_level") or "").strip() or estimate_risk_level(cur)
        rb = risk_badge_class(risk_tier)
        risk_esc = html.escape(risk_tier)
        risk_badge_html = f'<span class="{rb}">{risk_esc}</span>'

        card_html = f"""
<div class="ts-scan-inner ts-scan-inner--queue{sel_cls}">
  <div class="ts-scan-with-rank">
    <span class="ts-scan-rank" aria-label="Rank {rank_n}">{rank_label}</span>
    <div class="ts-scan-with-rank-body">
      <div class="ts-scan-title-row">
        <div class="ts-scan-title-full">{title}</div>
        {risk_badge_html}
      </div>
      <div class="ts-scan-score-block">
        <span class="ts-scan-lbl">Current Score</span>
        <span class="ts-scan-val ts-scan-val--current">{score_big}</span>
      </div>
      <div class="ts-scan-tags">{tag_bits}</div>
      <p class="ts-scan-desc">{summary}</p>
    </div>
  </div>
</div>
"""
        with _scan_card_container():
            st.markdown(card_html, unsafe_allow_html=True)
            _pad, _btn = st.columns([3, 1])
            with _btn:
                st.button(
                    "Details",
                    key=f"pq_det_{fp_key}_{i}",
                    on_click=_pick_pq,
                    args=(i,),
                    type="primary" if is_sel else "secondary",
                    use_container_width=True,
                )


def render_product_cards(
    df: pd.DataFrame,
    sort_key: str,
    forecast_by_asin: dict[str, dict] | None,
    fp_key: str,
) -> None:
    """Compact All results — full data only in the right panel after Details."""
    label = SORT_LABELS.get(sort_key, sort_key)
    n = len(df)
    st.markdown('<p class="section-label">All results</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="sort-hint">Sorted by <strong>{html.escape(label)}</strong> · {n:,} product{"s" if n != 1 else ""} in view</p>',
        unsafe_allow_html=True,
    )
    if df.empty:
        st.caption("Adjust filters to see products.")
        return

    fmap = forecast_by_asin or {}
    sel = st.session_state.get(SELECTED_PRODUCT_KEY)
    detail_open = bool(st.session_state.get(DETAIL_OPEN_KEY))

    def _select_row(idx: int) -> None:
        st.session_state[SELECTED_PRODUCT_KEY] = row_to_selected_product(df.iloc[int(idx)])
        st.session_state[DETAIL_OPEN_KEY] = True

    for row_idx, (_, row) in enumerate(df.iterrows()):
        aid = str(row.get("asin") or "")
        fr = fmap.get(aid) or {}
        title_plain = str(row.get("amazon_title") or "—")
        title = html.escape(title_plain[:82] + ("…" if len(title_plain) > 82 else ""))
        q = html.escape(str(row.get("query") or "—"))
        sc = float(row.get("opportunity_score") or 0)
        dt = fr.get("derived_tags") if fr else None
        dt_list = dt if isinstance(dt, list) else []
        tag_bits = "".join(
            f'<span class="pill-tag">{html.escape(str(t))}</span>' for t in dt_list[:3]
        )
        query_pill = f'<span class="pill-tag pill-tag--query">{q}</span>'
        summary = html.escape(_one_line_summary(row, fr if fr else None))
        if len(summary) > 118:
            summary = summary[:115] + "…"

        is_sel = detail_open and isinstance(sel, dict) and _same_listing_row(row, sel)
        sel_cls = " ts-scan-inner--selected" if is_sel else ""
        score_big = html.escape(f"{sc:.1f}")

        card_html = f"""
<div class="ts-scan-inner ts-scan-inner--all{sel_cls}">
  <div class="ts-scan-title-full">{title}</div>
  <div class="ts-scan-score-block">
    <span class="ts-scan-lbl">Current Score</span>
    <span class="ts-scan-val ts-scan-val--current">{score_big}</span>
  </div>
  <div class="ts-scan-tags">{query_pill}{tag_bits}</div>
  <p class="ts-scan-desc">{summary}</p>
</div>
"""
        with _scan_card_container():
            st.markdown(card_html, unsafe_allow_html=True)
            _pad, _btn = st.columns([3, 1])
            with _btn:
                st.button(
                    "Details",
                    key=f"ar_det_{fp_key}_{row_idx}",
                    on_click=_select_row,
                    args=(row_idx,),
                    type="primary" if is_sel else "secondary",
                    use_container_width=True,
                )


def main():
    st.set_page_config(
        page_title="SipScope",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if DETAIL_OPEN_KEY not in st.session_state:
        st.session_state[DETAIL_OPEN_KEY] = False

    df_all = load_products()
    render_header()

    if df_all.empty:
        st.stop()

    price_valid = df_all["price_num"].dropna()
    p_min_default = float(price_valid.min()) if len(price_valid) else 0.0
    p_max_default = float(price_valid.max()) if len(price_valid) else 500.0

    slider_max = max(500.0, p_max_default)

    col_filters, col_center = st.columns([1.0, 4.0], gap="large")

    with col_filters:
        sb = render_explore_sidebar(
            df_all,
            BENEFIT_CATEGORIES,
            p_min_default,
            p_max_default,
            slider_max,
        )

    search = sb["search"]
    q_pick = sb["q_pick"]
    benefit_pick = sb["benefit_pick"]
    min_rating = sb["min_rating"]
    pr_min = sb["pr_min"]
    pr_max = sb["pr_max"]
    sort_key = sb["sort_key"]

    filtered = apply_filters(
        df_all,
        search,
        q_pick,
        benefit_pick,
        min_rating,
        pr_min,
        pr_max,
    )
    sorted_df = sort_dataframe(filtered, sort_key)

    fp = filter_fingerprint(
        search,
        q_pick,
        benefit_pick,
        min_rating,
        pr_min,
        pr_max,
        len(filtered),
    )
    fp_key = hashlib.sha256(fp.encode()).hexdigest()[:16]

    fdf, upcoming_fc, forecast_by_asin = attach_forecast_to_dataframe(sorted_df)
    _sync_detail_selection(fdf)
    detail_open = bool(st.session_state.get(DETAIL_OPEN_KEY))

    top_fc = top_forecast_products(fdf, 5)
    top5 = top_recommendations(fdf)

    with col_center:
        render_metrics(sorted_df)
        render_forecast_intro(upcoming_fc)
        render_forecast_cards_only(top_fc, fdf, forecast_by_asin, fp_key)
        st.markdown('<hr class="sep"/>', unsafe_allow_html=True)
        render_recommended_block(top5, fdf, fp_key, forecast_by_asin)
        st.markdown('<hr class="sep"/>', unsafe_allow_html=True)
        render_product_cards(fdf, sort_key, forecast_by_asin, fp_key)

    if detail_open:
        with st.container():
            st.markdown(
                '<span class="ts-inspect-drawer-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            render_persistent_detail_panel(fdf, forecast_by_asin)


if __name__ == "__main__":
    main()