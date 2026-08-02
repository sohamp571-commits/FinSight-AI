"""
dashboard/top_gainers.py

Purpose: Computes and renders the Top Gainers table -- the highest
positive % movers in the tracked NSE large-cap universe -- using the
shared `render_movers_table` widget for a consistent Company / Price /
Change / Change % / Volume layout.
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


def render_top_gainers(limit: int = TOP_N) -> None:
    """Render the Top Gainers section, sorted by change % descending."""
    render_section_header("Top Gainers", subtitle=f"Top {limit} movers by % gain today", icon="📈")

    try:
        quotes = get_universe_quotes()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to fetch universe quotes for top gainers: {exc}")
        st.info("Top gainers data is temporarily unavailable.")
        return

    rows = _build_rows(quotes)
    gainers = sorted((r for r in rows if r["change_pct"] > 0), key=lambda r: r["change_pct"], reverse=True)[:limit]
    render_movers_table(gainers, empty_message="No gainers found in the current session.")
