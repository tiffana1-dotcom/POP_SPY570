"""Cross-source scoring, trend outlook, and risk for beverage SKUs."""

from __future__ import annotations

from typing import Any


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, n))


def recommendation_from_score(score: float) -> str:
    if score >= 72:
        return "Import"
    if score < 38:
        return "Avoid"
    return "Watch"


def build_opportunity(
    amazon: dict[str, Any],
    trends: dict[str, Any],
    reddit: dict[str, Any],
) -> dict[str, Any]:
    bsr = amazon.get("bsr")
    reviews = int(amazon.get("reviews") or 0)
    rating = amazon.get("rating")
    rating_f = float(rating) if isinstance(rating, (int, float)) else None

    # Amazon momentum proxy (lower BSR is better)
    bsr_score = 50.0
    if isinstance(bsr, int) and bsr > 0:
        bsr_score = _clamp(110.0 - (bsr ** 0.45))

    trend_idx = float(trends.get("interest_index") or 0)
    trend_score = _clamp(trend_idx * 0.85 + (12 if trends.get("ok") else 0))

    reddit_score = float(reddit.get("score") or 25)

    review_signal = _clamp(min(22.0, (reviews**0.35) * 3.2))
    rating_signal = 0.0
    if rating_f is not None:
        rating_signal = _clamp((rating_f - 3.9) * 18.0)

    raw = (
        bsr_score * 0.38
        + trend_score * 0.28
        + reddit_score * 0.20
        + review_signal * 0.10
        + rating_signal * 0.04
    )
    opportunity_score = int(round(_clamp(raw)))

    # Risk model
    risk_points = 0
    factors: list[str] = []
    if isinstance(bsr, int) and bsr > 0 and bsr < 80:
        risk_points += 2
        factors.append("Ultra-competitive BSR band — incumbent-heavy.")
    if reviews > 5000:
        risk_points += 1
        factors.append("High review count — hard to displace without differentiation.")
    if not trends.get("ok"):
        risk_points += 1
        factors.append("Google Trends signal weak or unavailable — demand less verified.")
    sig = str(reddit.get("signal") or "").lower()
    if sig == "low" or (isinstance(reddit.get("mentions"), int) and int(reddit.get("mentions") or 0) <= 3):
        risk_points += 1
        factors.append("Limited Reddit mentions across target beverage subs — social proof is thin.")

    if risk_points >= 4:
        level = "High"
    elif risk_points >= 2:
        level = "Medium"
    else:
        level = "Low"

    outlook_parts: list[str] = []
    if opportunity_score >= 70:
        outlook_parts.append("Cross-channel signals skew positive for near-term velocity.")
    elif opportunity_score >= 45:
        outlook_parts.append("Mixed but workable — validate pricing and differentiation before depth.")
    else:
        outlook_parts.append("Signals are cautious — better as a test buy or pass unless you have an edge.")

    ti = trends.get("change_note")
    if isinstance(ti, str) and ti:
        outlook_parts.append(f"Search: {ti}")
    rv = reddit.get("velocity_label")
    mentions = reddit.get("mentions")
    if isinstance(rv, str) and rv:
        mtxt = f" ~{int(mentions)} hits" if isinstance(mentions, int) else ""
        outlook_parts.append(f"Social: Reddit{mtxt} — {rv}.")

    rec = recommendation_from_score(float(opportunity_score))
    if level == "High" and rec == "Import":
        rec = "Watch"

    headline = (
        f"Amazon rank/reviews + search interest suggest {'strong' if opportunity_score >= 65 else 'moderate'} "
        f"beverage momentum (score {opportunity_score})."
    )

    bullets: list[str] = [
        headline,
        f"Amazon BSR (best category rank): #{bsr if isinstance(bsr, int) else 'n/a'} — lower is better.",
        f"Google Trends interest index (US, ~3m): ~{int(trend_idx)}.",
        f"Reddit: {int(reddit.get('mentions') or 0)} post hits across tracked subs (signal: {reddit.get('signal', 'n/a')}); "
        f"{len(reddit.get('posts') or [])} sample titles.",
    ]

    card_explanation = (headline[:110] + ("…" if len(headline) > 110 else "")).strip()

    return {
        "opportunity_score": opportunity_score,
        "recommendation": rec,
        "headline_reason": headline,
        "card_explanation": card_explanation,
        "explanation_bullets": bullets,
        "trend_outlook": " ".join(outlook_parts),
        "risk": {"level": level, "factors": factors[:6]},
    }
