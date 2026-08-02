"""
dashboard/market_heatmap.py

Purpose: Renders the Yahoo-Finance-style market heatmap -- a Plotly
treemap where every tile is a tracked ticker, tile size reflects the
magnitude of its move, and tile color reflects direction/intensity
(deep red -> neutral -> deep green). Built on top of
`chart_helpers.build_market_heatmap`.
"""

import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, build_market_heatmap
from dashboard.dashboard_layout import render_section_header
from dashboard.market_data_service import NIFTY50_UNIVERSE, get_universe_quotes
from logging_config import logger


def render_market_heatmap() -> None:
    """Render the full-universe market heatmap treemap."""
    render_section_header(
        "Market Heatmap",
        subtitle="Tile size = magnitude of move, color = direction & intensity",
        icon="🗺️",
    )

    try:
        quotes = get_universe_quotes()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to fetch universe quotes for heatmap: {exc}")
        st.info("Heatmap data is temporarily unavailable.")
        return

    if not quotes:
        st.info("No market data available to build the heatmap right now.")
        return

    rows = [
        {
            "ticker": ticker,
            "name": NIFTY50_UNIVERSE.get(ticker, ticker),
            "price": quote["price"],
            "change_pct": quote["change_pct"],
        }
        for ticker, quote in quotes.items()
    ]

    fig = build_market_heatmap(rows)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="market_heatmap_chart")
