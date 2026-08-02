"""
dashboard/market_indices.py

Purpose: Renders the primary "live market" KPI card grid: NIFTY 50,
SENSEX, BANK NIFTY, NASDAQ, DOW JONES, Gold, Silver, Bitcoin, and
USD/INR. This is the visual centerpiece of the Overview tab.
"""

import streamlit as st

from dashboard.dashboard_layout import render_section_header, responsive_columns
from dashboard.dashboard_widgets import render_kpi_card, render_kpi_card_placeholder
from dashboard.market_data_service import (
    ALL_OVERVIEW_SYMBOLS,
    COMMODITIES_AND_OTHERS,
    MARKET_INDICES,
    fetch_quotes_bulk,
)
from logging_config import logger

_CURRENCY_SYMBOLS = {
    "NIFTY 50": "₹",
    "SENSEX": "₹",
    "BANK NIFTY": "₹",
    "NASDAQ": "",
    "DOW JONES": "",
    "Gold": "$",
    "Silver": "$",
    "Bitcoin": "$",
    "USD/INR": "₹",
}


def _render_kpi_grid(labels_to_tickers: dict[str, str], quotes: dict[str, dict]) -> None:
    """Render a responsive grid of KPI cards for the given label->ticker mapping."""
    columns = responsive_columns(len(labels_to_tickers), max_cols=5)
    for column, (label, ticker) in zip(columns, labels_to_tickers.items()):
        with column:
            quote = quotes.get(ticker)
            if quote is None:
                render_kpi_card_placeholder(label)
                continue
            render_kpi_card(
                label=label,
                price=quote["price"],
                change=quote["change"],
                change_pct=quote["change_pct"],
                currency_symbol=_CURRENCY_SYMBOLS.get(label, ""),
            )


def render_market_indices() -> None:
    """Render the Indices section followed by the Commodities/Crypto/Forex section."""
    try:
        quotes = fetch_quotes_bulk(tuple(ALL_OVERVIEW_SYMBOLS.values()))
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to fetch overview quotes: {exc}")
        quotes = {}

    render_section_header("Global Indices", icon="🌐")
    _render_kpi_grid(MARKET_INDICES, quotes)

    st.write("")
    render_section_header("Commodities & Currency", icon="🪙")
    _render_kpi_grid(COMMODITIES_AND_OTHERS, quotes)
