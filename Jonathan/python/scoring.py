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
    walmart: dict[str, Any],
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

    walmart_bonus = 0.0
    walmart_risk_note = ""
    gap = str(walmart.get("gap") or "").lower()
    wm_count = walmart.get("walmart_count")
    if walmart.get("found"):
        if gap == "low":
            walmart_bonus = 10.0
        elif gap == "med":
            walmart_bonus = 7.0
        else:
            walmart_bonus = 6.0
        amz_p = amazon.get("price")
        wm_p = walmart.get("price")
        if isinstance(amz_p, (int, float)) and isinstance(wm_p, (int, float)) and wm_p > 0:
            spread = (wm_p - float(amz_p)) / float(amz_p)
            if spread < -0.12:
                walmart_risk_note = "Walmart priced meaningfully lower — margin pressure if you match Amazon shelf."
            elif spread > 0.15:
                walmart_risk_note = "Amazon priced below Walmart on this match — check MAP / parity risk."
    elif gap == "high" and isinstance(wm_count, int) and wm_count == 0:
        walmart_bonus = 5.0
        walmart_risk_note = "No Walmart catalog hits for this query — possible shelf gap or title mismatch vs Walmart taxonomy."

    review_signal = _clamp(min(22.0, (reviews**0.35) * 3.2))
    rating_signal = 0.0
    if rating_f is not None:
        rating_signal = _clamp((rating_f - 3.9) * 18.0)

    raw = (
        bsr_score * 0.34
        + trend_score * 0.26
        + reddit_score * 0.18
        + review_signal * 0.12
        + rating_signal * 0.06
        + walmart_bonus
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
    if walmart_risk_note:
        factors.append(walmart_risk_note)
    if isinstance(wm_count, int) and wm_count < 0:
        factors.append("Walmart search failed or credentials rejected — parity unknown.")
    elif not walmart.get("found") and gap != "high":
        factors.append("No Walmart match — retail parity unchecked for this title.")

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
    if isinstance(wm_count, int) and wm_count >= 0:
        bullets.append(
            f"Walmart: {wm_count} catalog hit(s), gap={gap or 'n/a'}"
            + (
                f" — {walmart.get('title', '')[:70]}"
                if walmart.get("found") and walmart.get("title")
                else ""
            )
            + (
                f", ${round(float(walmart['price']), 2)}"
                if isinstance(walmart.get("price"), (int, float))
                else ""
            )
            + ".",
        )

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
