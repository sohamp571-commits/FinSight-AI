"""
market_intelligence/ipo_calendar.py

Purpose: Renders the IPO Calendar tab -- Upcoming / Current (Open) /
Closed / Listed IPOs as sub-tabs, each backed by
`ipo_service.get_by_status()`. Seeds sample data on first load so the
module is demoable without a live IPO data feed (see
`ipo_service.seed_sample_ipos()`'s docstring).
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header
from helper import format_currency, format_date
from market_intelligence.ipo_service import ipo_service

_STATUS_TABS = [("UPCOMING", "🗓️ Upcoming"), ("OPEN", "🟢 Current"), ("CLOSED", "🔴 Closed"), ("LISTED", "✅ Listed")]


def _render_ipo_card(ipo) -> None:
    """Render a single IPO summary card within the calendar."""
    price_range = (
        f"{format_currency(ipo.issue_price_min, '₹')} – {format_currency(ipo.issue_price_max, '₹')}"
        if ipo.issue_price_min and ipo.issue_price_max
        else "Not yet announced"
    )

    with st.container():
        st.markdown(f"### {ipo.company_name}")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.caption("Issue Price")
            st.write(price_range)
        with col2:
            st.caption("Open Date")
            st.write(format_date(ipo.open_date) if ipo.open_date else "TBA")
        with col3:
            st.caption("Close Date")
            st.write(format_date(ipo.close_date) if ipo.close_date else "TBA")
        with col4:
            st.caption("Listing Date")
            st.write(format_date(ipo.listing_date) if ipo.listing_date else "TBA")

        if ipo.subscription_times is not None:
            st.caption(f"📊 Subscribed **{float(ipo.subscription_times):.2f}x**" + (f" • GMP: {format_currency(ipo.gmp, '₹')}" if ipo.gmp else ""))
        st.markdown("---")


def render_ipo_calendar() -> None:
    """Render the full IPO Calendar tab with status sub-tabs."""
    render_section_header("IPO Calendar", icon="📅")

    seeded = ipo_service.seed_sample_ipos()
    if seeded:
        st.caption(f"Loaded {seeded} sample IPO listing(s) to populate the calendar.")
    ipo_service.refresh_all_statuses()

    tab_labels = [label for _, label in _STATUS_TABS]
    tabs = st.tabs(tab_labels)

    for tab, (status, _) in zip(tabs, _STATUS_TABS):
        with tab:
            result = ipo_service.get_by_status(status, page_size=50)
            if not result["items"]:
                st.info(f"No {status.lower()} IPOs at the moment.")
                continue
            for ipo in result["items"]:
                _render_ipo_card(ipo)
