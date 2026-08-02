"""
stock_search/stock_statistics.py

Purpose: Renders the "Market Information" statistics grid -- current
price, open, previous close, day high/low, 52-week high/low, volume,
average volume, market cap, beta, P/E ratio, EPS, dividend yield, and
book value. Pulls from the same cached `company_profile.get_company_info()`
call rather than issuing a second yfinance request.
"""

from typing import Any

import streamlit as st

from dashboard.dashboard_layout import render_section_header, responsive_columns
from helper import format_currency, format_percentage
from stock_search.company_profile import get_company_info


def _metric(label: str, value: str) -> None:
    """Render a single labeled statistic using Streamlit's native metric widget."""
    st.metric(label, value)


def _currency_symbol(ticker: str) -> str:
    return "₹" if (".NS" in ticker or ".BO" in ticker) else "$"


def render_stock_statistics(ticker: str) -> None:
    """Render the full Market Information statistics grid for a ticker."""
    info: dict[str, Any] | None = get_company_info(ticker)
    if info is None:
        st.info(f"Market statistics are not available for {ticker}.")
        return

    currency = _currency_symbol(ticker)
    price = info.get("currentPrice") or info.get("regularMarketPrice")

    render_section_header("Market Information", icon="📊")

    stats: list[tuple[str, str]] = [
        ("Current Price", format_currency(price, currency) if price else "N/A"),
        ("Open", format_currency(info.get("open"), currency) if info.get("open") else "N/A"),
        ("Previous Close", format_currency(info.get("previousClose"), currency) if info.get("previousClose") else "N/A"),
        ("Day High", format_currency(info.get("dayHigh"), currency) if info.get("dayHigh") else "N/A"),
        ("Day Low", format_currency(info.get("dayLow"), currency) if info.get("dayLow") else "N/A"),
        ("52 Week High", format_currency(info.get("fiftyTwoWeekHigh"), currency) if info.get("fiftyTwoWeekHigh") else "N/A"),
        ("52 Week Low", format_currency(info.get("fiftyTwoWeekLow"), currency) if info.get("fiftyTwoWeekLow") else "N/A"),
        ("Volume", f"{info.get('volume'):,}" if info.get("volume") else "N/A"),
        ("Average Volume", f"{info.get('averageVolume'):,}" if info.get("averageVolume") else "N/A"),
        ("Market Cap", format_currency(info.get("marketCap"), currency) if info.get("marketCap") else "N/A"),
        ("Beta", f"{info.get('beta'):.2f}" if info.get("beta") is not None else "N/A"),
        ("P/E Ratio", f"{info.get('trailingPE'):.2f}" if info.get("trailingPE") is not None else "N/A"),
        ("EPS", format_currency(info.get("trailingEps"), currency) if info.get("trailingEps") is not None else "N/A"),
        ("Dividend Yield", format_percentage(info.get("dividendYield") * 100) if info.get("dividendYield") else "N/A"),
        ("Book Value", format_currency(info.get("bookValue"), currency) if info.get("bookValue") is not None else "N/A"),
    ]

    for row_start in range(0, len(stats), 5):
        row = stats[row_start:row_start + 5]
        columns = responsive_columns(len(row), max_cols=5)
        for column, (label, value) in zip(columns, row):
            with column:
                _metric(label, value)
