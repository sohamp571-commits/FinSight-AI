"""
market_intelligence/ipo_subscription.py

Purpose: Renders a focused Subscription Status view -- a comparison
table/chart of every currently OPEN IPO's subscription multiple and
GMP, letting a user quickly see which open IPOs are most in demand
without opening each one's detail page individually.
"""

import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, COLOR_ACCENT, apply_dark_theme
from dashboard.dashboard_layout import render_section_header
from helper import format_currency
from market_intelligence.ipo_service import ipo_service


def render_ipo_subscription_status() -> None:
    """Render the Subscription Status tab for all currently open IPOs."""
    render_section_header("IPO Subscription Status", subtitle="Currently open IPOs", icon="📊")

    open_ipos = ipo_service.get_by_status("OPEN", page_size=50)["items"]
    if not open_ipos:
        st.info("No IPOs are currently open for subscription.")
        return

    rows = [
        {
            "Company": ipo.company_name,
            "Subscription": float(ipo.subscription_times) if ipo.subscription_times is not None else 0.0,
            "GMP": format_currency(ipo.gmp, "₹") if ipo.gmp is not None else "N/A",
            "Price Band": (
                f"{format_currency(ipo.issue_price_min, '₹')} – {format_currency(ipo.issue_price_max, '₹')}"
                if ipo.issue_price_min and ipo.issue_price_max else "N/A"
            ),
        }
        for ipo in open_ipos
    ]

    fig = go.Figure(
        go.Bar(
            x=[row["Company"] for row in rows],
            y=[row["Subscription"] for row in rows],
            marker_color=COLOR_ACCENT,
            text=[f"{row['Subscription']:.2f}x" for row in rows],
            textposition="outside",
        )
    )
    fig.update_layout(title="Subscription Multiple by IPO", yaxis_title="Times Subscribed")
    fig = apply_dark_theme(fig, height=360)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="ipo_subscription_chart")

    st.dataframe(rows, use_container_width=True, hide_index=True)
