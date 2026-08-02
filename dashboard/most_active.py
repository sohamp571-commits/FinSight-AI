"""
dashboard/most_active.py

Purpose: Computes and renders the Most Active table -- the highest
trading-volume tickers in the tracked universe -- using the same
shared table widget as top_gainers.py/top_losers.py for visual
consistency.
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header
from dashboard.dashboard_widgets import render_movers_table
from dashboard.market_data_service import NIFTY50_UNIVERSE, get_universe_quotes
from logging_config import logger

TOP_N = 10


def _build_rows(quotes: dict) -> list[dict]:
    """Convert raw quote dicts into the row shape expected by render_movers_table."""
    rows = []
    for ticker, quote in quotes.items():
        rows.append(
            {
                "ticker": ticker,
                "company": NIFTY50_UNIVERSE.get(ticker, ticker),
                "price": quote["price"],
                "change": quote["change"],
                "change_pct": quote["change_pct"],
                "volume": quote["volume"],
            }
        )
    return rows


def render_most_active(limit: int = TOP_N) -> None:
    """Render the Most Active section, sorted by trading volume descending."""
    render_section_header("Most Active", subtitle=f"Top {limit} tickers by trading volume today", icon="🔥")

    try:
        quotes = get_universe_quotes()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to fetch universe quotes for most active: {exc}")
        st.info("Most active data is temporarily unavailable.")
        return

    rows = _build_rows(quotes)
    most_active = sorted(rows, key=lambda r: r["volume"], reverse=True)[:limit]
    render_movers_table(most_active, empty_message="No volume data available for the current session.")
