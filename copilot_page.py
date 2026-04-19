"""Buyer Decision Assistant UI (used on the dedicated multipage route)."""

from __future__ import annotations

import html
import os
from typing import Callable, Literal

import pandas as pd
import streamlit as st

import env_setup

env_setup.load_pop_dotenv()

from buyer_copilot import analyze_product, format_product_context_for_analysis

AsinSource = Literal["radio", "select"]


def _copilot_rec_badge_class(recommendation: str) -> str:
    return {
        "Recommend": "copilot-badge rec-ok",
        "Recommend with Review": "copilot-badge rec-review",
        "Needs Manual Review": "copilot-badge rec-manual",
        "Do Not Recommend Yet": "copilot-badge rec-no",
    }.get(recommendation, "copilot-badge rec-review")


def _copilot_conf_badge_class(confidence: str) -> str:
    return {
        "Low": "copilot-badge conf-low",
        "Medium": "copilot-badge conf-med",
        "High": "copilot-badge conf-high",
    }.get(confidence, "copilot-badge conf-med")


def render_copilot_gpt_result(
    result: dict,
    *,
    show_heading: bool = True,
    use_chat_message: bool = True,
) -> None:
    """Structured GPT buyer screening output (Buyer Assistant page + TrendScout detail drawer)."""
    if not isinstance(result, dict) or not result:
        return
    if show_heading:
        st.markdown("##### Assistant output")
    rec = result.get("recommendation", "")
    conf = result.get("confidence", "")
    rb = _copilot_rec_badge_class(rec)
    cb = _copilot_conf_badge_class(conf)
    summary = html.escape(str(result.get("summary") or ""))

    def ul(items: list) -> str:
        if not items:
            return "<p class='copilot-summary' style='color:var(--text-muted)'>—</p>"
        li = "".join(f"<li>{html.escape(str(x))}</li>" for x in items)
        return f"<ul class='copilot-list'>{li}</ul>"

    inner = f"""
<div class="copilot-result-card" style="margin-top:0">
  <div class="copilot-badge-row">
    <span class="{rb}">{html.escape(rec)}</span>
    <span class="{cb}">Confidence: {html.escape(conf)}</span>
  </div>
  <div class="copilot-section-title">Summary</div>
  <p class="copilot-summary">{summary}</p>
  <div class="copilot-section-title">Potential benefits</div>
  {ul(result.get("benefits") or [])}
  <div class="copilot-section-title">Potential risks / concerns</div>
  {ul(result.get("risks") or [])}
  <div class="copilot-section-title">Regulatory / claim flags</div>
  {ul(result.get("regulatory_flags") or [])}
  <div class="copilot-section-title">Manual checks</div>
  {ul(result.get("manual_checks") or [])}
</div>
"""
    if use_chat_message:
        with st.chat_message("assistant"):
            st.markdown(inner, unsafe_allow_html=True)
    else:
        st.markdown(inner, unsafe_allow_html=True)


def render_buyer_copilot_section(
    df_all: pd.DataFrame,
    top5: pd.DataFrame,
    fp: str,
    *,
    asin_source: AsinSource = "select",
    format_rec_radio_label: Callable[[str, pd.DataFrame], str] | None = None,
) -> None:
    """
    Buyer screening assistant with optional ASIN source:
    - ``select``: pick from top-5 opportunities (assistant page).
    - ``radio``: use dashboard ``rec_radio_{fp}`` (if embedded on dashboard).
    """
    fmt = format_rec_radio_label or (lambda a, t: str(a))

    has_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    if not has_key:
        st.error(
            "OPENAI_API_KEY is not set. Add it to `.env` in the project root or to `app/.env`, "
            "or export it in your shell, then restart Streamlit."
        )

    st.markdown(
        """
<div class="copilot-hero">
  <p class="copilot-hero-kicker">Decision support</p>
  <p class="copilot-hero-title">Buyer Decision Assistant</p>
  <p class="copilot-hero-sub">
    Screening assistant for procurement — not medical or legal advice. Paste listing details, edit as needed, then run analysis.
    The model returns structured JSON, shown below as an assistant reply.
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    k_name = f"copilot_name_{fp}"
    k_info = f"copilot_info_{fp}"
    k_result = f"copilot_result_{fp}"
    k_err = f"copilot_err_{fp}"
    k_asin_pick = f"copilot_asin_pick_{fp}"
    k_fill_warn = f"_copilot_fill_warn_{fp}"
    radio_key = f"rec_radio_{fp}"

    if k_name not in st.session_state:
        st.session_state[k_name] = ""
    if k_info not in st.session_state:
        st.session_state[k_info] = ""

    def _on_fill_listing() -> None:
        """Runs before the rest of the script so we can set widget session keys safely."""
        asin: str | None = None
        if asin_source == "select":
            asin = st.session_state.get(k_asin_pick)
        else:
            asin = st.session_state.get(radio_key)

        row = None
        if asin and not top5.empty:
            hit = top5[top5["asin"] == asin]
            if not hit.empty:
                row = hit.iloc[0]
        if row is None and asin and not df_all.empty:
            hit = df_all[df_all["asin"] == asin]
            if not hit.empty:
                row = hit.iloc[0]
        if row is None:
            st.session_state[k_fill_warn] = (
                "Choose a listing (top opportunities dropdown) or select a product on the **TrendScout dashboard** first, "
                "then try again."
            )
            return
        st.session_state.pop(k_fill_warn, None)
        t, blob = format_product_context_for_analysis(row)
        st.session_state[k_name] = t
        st.session_state[k_info] = blob

    msg = st.session_state.pop(k_fill_warn, None)
    if isinstance(msg, str) and msg.strip():
        st.warning(msg)

    if asin_source == "select" and not top5.empty:
        asins = top5["asin"].tolist()
        st.selectbox(
            "Load from top opportunities (same ranking as dashboard)",
            options=asins,
            format_func=lambda a: fmt(a, top5),
            key=k_asin_pick,
            help="Chooses which SKU to pull listing text from when you click Fill.",
        )

    st.markdown("##### Input")
    product_name = st.text_input(
        "Product name",
        placeholder="Listing title or short name",
        key=k_name,
        disabled=not has_key,
    )
    product_info = st.text_area(
        "Product information",
        height=200,
        placeholder=(
            "Category, bullets, ingredients, benefits, shelf life, rating, reviews, price, brand, "
            "regulatory snippets…"
        ),
        key=k_info,
        help="Edit freely before analysis. Loaded text is a best-effort extract from the listing.",
        disabled=not has_key,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.button(
            "Fill from selected listing",
            use_container_width=True,
            disabled=not has_key,
            help="Fills fields from the ASIN chosen above (or from the dashboard radio when using dashboard mode).",
            on_click=_on_fill_listing,
        )
    with c2:
        run = st.button(
            "Analyze Product",
            type="primary",
            use_container_width=True,
            disabled=not has_key,
        )

    if run and has_key:
        st.session_state[k_err] = None
        st.session_state[k_result] = None
        try:
            st.session_state[k_result] = analyze_product(product_name, product_info)
        except Exception as e:
            st.session_state[k_err] = str(e)
        st.rerun()

    err = st.session_state.get(k_err)
    if err:
        st.error(f"Analysis failed: {html.escape(err)}")

    result = st.session_state.get(k_result)
    if isinstance(result, dict) and result:
        render_copilot_gpt_result(result, show_heading=True, use_chat_message=True)
