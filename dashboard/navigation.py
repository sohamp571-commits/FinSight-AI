"""
dashboard/navigation.py

Purpose: Defines the dashboard's internal tab navigation (Overview,
Gainers & Losers, Most Active, Heatmap). Kept separate from
`authentication/middleware.py`'s page-level routing -- that decides
*whether* you can see the dashboard at all; this decides *which
section* of the dashboard you're looking at once you're in.
"""

import streamlit as st

DASHBOARD_TABS: list[tuple[str, str]] = [
    ("overview", "📊 Overview"),
    ("gainers_losers", "📈 Gainers & Losers"),
    ("most_active", "🔥 Most Active"),
    ("heatmap", "🗺️ Heatmap"),
]


def render_navigation():
    """
    Render the dashboard's tab bar using `st.tabs` (native, no extra
    dependency). Returns the tab container objects paired with their
    keys so the caller (dashboard.py) can dispatch section content
    into each one:

        tab_objects, tab_keys = render_navigation()
        for tab, key in zip(tab_objects, tab_keys):
            with tab:
                dispatch(key)
    """
    labels = [label for _, label in DASHBOARD_TABS]
    keys = [key for key, _ in DASHBOARD_TABS]
    tab_objects = st.tabs(labels)
    return tab_objects, keys
