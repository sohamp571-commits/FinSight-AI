"""
dashboard/market_overview.py

Purpose: Assembles the "Overview" tab: market status badge, the full
indices/commodities KPI grid, and a personalized snapshot of the
logged-in user's portfolio and watchlist size -- this is the one
place in the dashboard module that reaches into the Phase 3 CRUD
service layer, tying the live-market view back to the user's own data.
"""

import streamlit as st

from authentication.session_manager import get_current_user_id
from custom_exceptions import FinSightBaseException
from database.portfolio_service import portfolio_service
from database.watchlist_service import watchlist_service
from dashboard.dashboard_layout import render_divider, render_section_header
from dashboard.dashboard_widgets import render_snapshot_metric
from dashboard.market_indices import render_market_indices
from dashboard.market_status import render_market_status_section
from helper import format_currency, format_percentage
from logging_config import logger


def _render_user_snapshot() -> None:
    """Render a compact portfolio value / P&L / watchlist-size snapshot for the current user."""
    user_id = get_current_user_id()
    if user_id is None:
        return

    render_section_header("Your Snapshot", icon="💼")
    try:
        summary = portfolio_service.portfolio_summary(user_id)
        watchlist_count = watchlist_service.count(filters={"user_id": user_id})

        col1, col2, col3 = st.columns(3)
        with col1:
            render_snapshot_metric("Invested", format_currency(summary["total_invested"], "₹"))
        with col2:
            pnl = summary["total_profit_loss"]
            render_snapshot_metric(
                "Current Value",
                format_currency(summary["total_current_value"], "₹"),
                delta=f"{format_currency(pnl, '₹')} ({format_percentage(summary['total_profit_loss_pct'])})",
            )
        with col3:
            render_snapshot_metric("Watchlist", f"{watchlist_count} ticker(s)")

        if not summary["holdings"]:
            st.caption("You have no holdings yet. Buy your first stock from the Portfolio module to see it here.")
    except FinSightBaseException as exc:
        logger.error(f"Failed to load user snapshot on dashboard: {exc}")
        st.info("Your portfolio snapshot is temporarily unavailable.")


def render_overview_tab() -> None:
    """Render the full Overview tab content."""
    render_market_status_section()
    st.write("")
    render_market_indices()
    render_divider()
    _render_user_snapshot()
