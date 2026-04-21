"""Shared Explore sidebar for SipScope dashboard + Buyer Assistant (same widget keys = shared state)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

# String option values only — tuple options in selectbox can break session-state round-trips.
SORT_LABELS: dict[str, str] = {
    "best_opportunity": "Best opportunity score",
    "highest_rating": "Highest rating",
    "most_reviews": "Most reviews",
    "lowest_price": "Lowest price",
}
_SORT_OPTION_KEYS: tuple[str, ...] = tuple(SORT_LABELS.keys())


def render_explore_sidebar(
    df_all: pd.DataFrame,
    benefit_categories: dict[str, dict[str, Any]],
    p_min_default: float,
    p_max_default: float,
    slider_max: float,
) -> dict[str, Any]:
    """Render filter widgets in the **current** Streamlit container.

    Call inside ``with st.sidebar:`` for a classic sidebar, or inside ``with col:`` for a dashboard column.
    Returns values for apply_filters / fingerprint.
    """
    st.markdown("### Filters")
    search = st.text_input(
        "Search",
        placeholder="Title, query, ASIN…",
        help="Filter the table by text match.",
        key="ts_search",
    )
    queries = sorted(df_all["query"].unique().tolist())
    q_pick = st.multiselect(
        "Query / category",
        options=queries,
        default=[],
        help="Limit to one or more search queries.",
        key="ts_q_pick",
    )
    st.caption("PRODUCT BENEFITS")
    benefit_keys = list(benefit_categories.keys())
    benefit_pick = st.multiselect(
        "Product benefits categories",
        options=benefit_keys,
        default=[],
        format_func=lambda k: str(benefit_categories[k]["label"]),
        help=(
            "Keep products whose **Product benefits** field matches at least one selected theme "
            "(keyword match). Leave empty to show all."
        ),
        key="ts_benefit_pick",
    )
    st.markdown("---")
    st.caption("QUALITY")
    min_rating = st.slider(
        "Minimum rating", 0.0, 5.0, 0.0, 0.1, key="ts_min_rating"
    )
    st.caption("PRICE")
    pr_min, pr_max = st.slider(
        "Range (USD)",
        min_value=0.0,
        max_value=slider_max,
        value=(p_min_default, p_max_default),
        step=0.5,
        key="ts_price_range",
    )
    st.markdown("---")
    st.caption("ORDER")
    sort_key = st.selectbox(
        "Sort results by",
        options=list(_SORT_OPTION_KEYS),
        format_func=lambda k: SORT_LABELS[k],
        key="ts_sort_order",
    )

    return {
        "search": search,
        "q_pick": q_pick,
        "benefit_pick": benefit_pick,
        "min_rating": min_rating,
        "pr_min": pr_min,
        "pr_max": pr_max,
        "sort_key": sort_key,
    }
