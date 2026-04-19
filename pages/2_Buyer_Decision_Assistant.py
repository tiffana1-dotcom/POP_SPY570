"""Buyer Decision Assistant — dedicated page (chat-style analysis)."""

from __future__ import annotations

import env_setup

env_setup.load_pop_dotenv()

import streamlit as st

from copilot_page import render_buyer_copilot_section
from TrendScout import (
    BENEFIT_CATEGORIES,
    apply_filters,
    filter_fingerprint,
    format_rec_radio_label,
    load_products,
    render_header,
    sort_dataframe,
    top_recommendations,
)
from trendscout_sidebar import render_explore_sidebar


def main() -> None:
    st.set_page_config(
        page_title="Buyer Decision Assistant | TrendScout",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    df_all = load_products()
    render_header()

    if df_all.empty:
        st.stop()

    price_valid = df_all["price_num"].dropna()
    p_min_default = float(price_valid.min()) if len(price_valid) else 0.0
    p_max_default = float(price_valid.max()) if len(price_valid) else 500.0
    slider_max = max(500.0, p_max_default)

    with st.sidebar:
        sb = render_explore_sidebar(
            df_all,
            BENEFIT_CATEGORIES,
            p_min_default,
            p_max_default,
            slider_max,
        )

    filtered = apply_filters(
        df_all,
        sb["search"],
        sb["q_pick"],
        sb["benefit_pick"],
        sb["min_rating"],
        sb["pr_min"],
        sb["pr_max"],
    )

    fp = filter_fingerprint(
        sb["search"],
        sb["q_pick"],
        sb["benefit_pick"],
        sb["min_rating"],
        sb["pr_min"],
        sb["pr_max"],
        len(filtered),
    )

    sorted_df = sort_dataframe(filtered, sb["sort_key"])
    top5 = top_recommendations(sorted_df)

    render_buyer_copilot_section(
        df_all,
        top5,
        fp,
        asin_source="select",
        format_rec_radio_label=format_rec_radio_label,
    )


if __name__ == "__main__":
    main()
