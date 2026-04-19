"""
Buyer Decision Assistant — GPT-backed product screening (not medical/regulatory advice).

Requires ``OPENAI_API_KEY`` (or pass ``api_key`` to ``analyze_product``).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import pandas as pd

try:
    import env_setup

    env_setup.load_pop_dotenv()
except ImportError:
    pass

RECOMMENDATION_LEVELS: tuple[str, ...] = (
    "Recommend",
    "Recommend with Review",
    "Needs Manual Review",
    "Do Not Recommend Yet",
)

CONFIDENCE_LEVELS: tuple[str, ...] = ("Low", "Medium", "High")

BUYER_COPILOT_SYSTEM_PROMPT = """You are a **buyer screening assistant** for retail / e‑commerce sourcing. You help procurement teams triage listings using the text and metrics provided.

**Role boundaries**
- You are NOT a doctor, lawyer, regulator, or compliance officer. Do not present yourself as one.
- Do not state or imply FDA (or other agency) approval, clearance, or endorsement unless the user’s text explicitly says so verbatim; if unclear, flag it for manual verification.
- You give **practical screening guidance**, not definitive safety or legal conclusions.

**What to analyze**
- Separate **commercial attractiveness** (reviews, price, positioning) from **claim / compliance risk** (health, structure/function, disease, guaranteed outcomes).
- Flag **suspicious or aggressive** health/medical/wellness claims, implied cures, weight-loss promises, or “clinically proven” without support in the provided text.
- Note **missing information** that would normally be needed for a confident buyer decision (ingredients incomplete, shelf life unknown, etc.).
- Be **concise, structured, professional**. Avoid casual chat.

**Uncertainty**
- When evidence is incomplete or only marketing copy is available, recommend **manual review** and lower confidence.
- Never overstate certainty.

**Output format**
Respond with **only** a single JSON object (no markdown fences, no commentary). Use this schema exactly:
{
  "summary": "string, 2-4 sentences",
  "benefits": ["string", "..."],
  "risks": ["string", "..."],
  "regulatory_flags": ["string", "..."],
  "recommendation": "one of: Recommend | Recommend with Review | Needs Manual Review | Do Not Recommend Yet",
  "confidence": "one of: Low | Medium | High",
  "manual_checks": ["string", "..."]
}

**Recommendation guide**
- **Recommend**: Strong commercial signals and claims look proportionate / low drama for the category, or issues are minor.
- **Recommend with Review**: Worth pursuing but verify specific claims, labeling, or supplier docs.
- **Needs Manual Review**: Material gaps, ambiguous claims, or mixed risk signals.
- **Do Not Recommend Yet**: Serious red flags, irresponsible claims, or insufficient data to list responsibly without more diligence.

**Confidence guide**
- **High**: Rich, consistent product text + metrics; few ambiguities.
- **Medium**: Usable but some gaps or moderate claim risk.
- **Low**: Sparse data, heavy marketing, or high claim uncertainty.
"""


def build_user_message(product_name: str, product_info: str) -> str:
    name = (product_name or "").strip() or "(no title provided)"
    body = (product_info or "").strip() or "(no product details provided)"
    return (
        "Analyze this product listing for a buyer pre-screen.\n\n"
        f"**Product name / title:** {name}\n\n"
        f"**Product information (may include bullets, ingredients, benefits, shelf life, price, brand, reviews, regulatory snippets):**\n{body}"
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
    if fence:
        t = fence.group(1).strip()
    return json.loads(t)


def normalize_analysis_dict(data: dict[str, Any]) -> dict[str, Any]:
    rec = str(data.get("recommendation", "")).strip()
    if rec not in RECOMMENDATION_LEVELS:
        rec = _fuzzy_enum(rec, RECOMMENDATION_LEVELS, "Needs Manual Review")

    conf = str(data.get("confidence", "")).strip()
    if conf not in CONFIDENCE_LEVELS:
        conf = _fuzzy_enum(conf, CONFIDENCE_LEVELS, "Medium")

    def as_list(v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    return {
        "summary": str(data.get("summary") or "").strip() or "No summary returned.",
        "benefits": as_list(data.get("benefits")),
        "risks": as_list(data.get("risks")),
        "regulatory_flags": as_list(data.get("regulatory_flags")),
        "recommendation": rec,
        "confidence": conf,
        "manual_checks": as_list(data.get("manual_checks")),
    }


def _fuzzy_enum(val: str, allowed: tuple[str, ...], default: str) -> str:
    v = val.strip()
    if v in allowed:
        return v
    vl = v.lower()
    for a in sorted(allowed, key=len, reverse=True):
        al = a.lower()
        if al in vl or vl in al:
            return a
    return default


def analyze_product_with_openai(
    product_name: str,
    product_info: str,
    *,
    api_key: str,
    model: str | None = None,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("Install the `openai` package: pip install openai") from e

    client = OpenAI(api_key=api_key)
    m = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    user_msg = build_user_message(product_name, product_info)

    resp = client.chat.completions.create(
        model=m,
        temperature=0.25,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": BUYER_COPILOT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    if not raw:
        raise ValueError("Empty response from model")
    parsed = _extract_json_object(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Model did not return a JSON object")
    return normalize_analysis_dict(parsed)


def analyze_product(
    product_name: str,
    product_info: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to `.env` in the project root or `app/.env`, "
            "or export it in your environment, then restart the app."
        )
    return analyze_product_with_openai(product_name, product_info, api_key=key, model=model)


def _bullets_lines(row: pd.Series) -> str:
    b = row.get("bullets")
    if isinstance(b, list) and b:
        return "\n".join(f"- {x}" for x in b)
    return ""


def _brand_from_row(row: pd.Series) -> str:
    for col in ("brand", "Brand", "manufacturer"):
        if col in row.index and pd.notna(row.get(col)):
            s = str(row[col]).strip()
            if s:
                return s
    item = row.get("item_details")
    if isinstance(item, dict):
        for k, v in item.items():
            if "manufacturer" in k.lower() and v and str(v).strip():
                return str(v).strip()[:300]
    dr = row.get("detail_rows")
    if isinstance(dr, dict):
        for k, v in dr.items():
            if "manufacturer" in k.lower() and v and str(v).strip():
                return str(v).strip()[:300]
    return ""


def _regulatory_snippet(row: pd.Series, max_chars: int = 1200) -> str:
    chunks: list[str] = []
    for key in ("important_information", "detail_rows", "item_details"):
        val = row.get(key)
        if isinstance(val, dict) and val:
            try:
                chunks.append(json.dumps(val, ensure_ascii=False)[: max_chars // 3])
            except (TypeError, ValueError):
                chunks.append(str(val)[: max_chars // 3])
    out = "\n".join(chunks)
    return out[:max_chars] if out else ""


def format_product_context_for_analysis(row: pd.Series) -> tuple[str, str]:
    title = str(row.get("amazon_title") or row.get("search_result_title") or "").strip() or "—"
    lines: list[str] = []
    q = str(row.get("query") or "").strip()
    if q:
        lines.append(f"Category / search query: {q}")
    brand = _brand_from_row(row)
    if brand:
        lines.append(f"Brand / manufacturer (best effort): {brand}")
    p = row.get("price")
    if p is not None and str(p).strip():
        lines.append(f"Price: {p}")
    r = row.get("rating")
    if pd.notna(r):
        lines.append(f"Rating: {float(r):.1f} / 5")
    rc = row.get("review_count")
    if pd.notna(rc):
        lines.append(f"Review count: {int(rc)}")
    sl = str(row.get("product_shelf_life") or "").strip()
    if not sl and "Product Shelf Life" in row.index:
        sl = str(row.get("Product Shelf Life") or "").strip()
    if sl:
        lines.append(f"Shelf life: {sl}")
    ben = str(row.get("product_benefits") or "").strip()
    if not ben and "Product Benefits" in row.index:
        ben = str(row.get("Product Benefits") or "").strip()
    if ben:
        lines.append(f"Product benefits (listing): {ben}")
    ing = row.get("Special Ingredients")
    if ing is not None and str(ing).strip():
        lines.append(f"Special ingredients (if listed): {ing}")
    reg = str(row.get("region_of_origin") or "").strip()
    if not reg and "Region of Origin" in row.index:
        reg = str(row.get("Region of Origin") or "").strip()
    if reg:
        lines.append(f"Region of origin: {reg}")
    bl = _bullets_lines(row)
    if bl:
        lines.append("Bullets:")
        lines.append(bl)
    reg = _regulatory_snippet(row)
    if reg:
        lines.append("Additional listing / detail JSON (truncated):")
        lines.append(reg)
    asin = str(row.get("asin") or "").strip()
    if asin:
        lines.append(f"ASIN: {asin}")
    return title, "\n".join(lines)
