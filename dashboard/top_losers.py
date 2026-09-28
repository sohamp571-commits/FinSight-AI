"""
dashboard/top_losers.py

Purpose: Computes and renders the Top Losers table -- the largest
negative % movers in the tracked NSE large-cap universe -- mirroring
top_gainers.py's structure exactly, sorted in the opposite direction.
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header
from dashboard.dashboard_widgets import build_mover_rows, render_movers_table
from dashboard.market_data_service import get_universe_quotes
from logging_config import logger

TOP_N = 10


def render_top_losers(limit: int = TOP_N) -> None:
    """Render the Top Losers section, sorted by change % ascending (most negative first)."""
    render_section_header("Top Losers", subtitle=f"Top {limit} movers by % loss today", icon="📉")

    try:
        quotes = get_universe_quotes()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to fetch universe quotes for top losers: {exc}")
        st.info("Top losers data is temporarily unavailable.")
        return

    rows = build_mover_rows(quotes)
    losers = sorted((r for r in rows if r["change_pct"] < 0), key=lambda r: r["change_pct"])[:limit]
    render_movers_table(losers, empty_message="No losers found in the current session.")