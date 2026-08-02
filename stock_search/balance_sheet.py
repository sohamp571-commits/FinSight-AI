"""
stock_search/balance_sheet.py

Purpose: Fetches and renders a company's Balance Sheet (annual and
quarterly) from yfinance. `get_balance_sheet()` is reused by
fundamental_analysis.py for ratios like Debt-to-Equity, Current Ratio,
and Quick Ratio.
"""

import time

import pandas as pd
import streamlit as st
import yfinance as yf

from custom_exceptions import ExternalAPIError
from dashboard.dashboard_layout import render_section_header
from logging_config import logger

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 1.5

_KEY_ROWS = [
    "Total Assets",
    "Total Liabilities Net Minority Interest",
    "Total Equity Gross Minority Interest",
    "Current Assets",
    "Current Liabilities",
    "Total Debt",
    "Cash And Cash Equivalents",
]


@st.cache_data(ttl=3600, show_spinner=False)
def get_balance_sheet(ticker: str, quarterly: bool = False) -> pd.DataFrame | None:
    """Fetch the balance sheet for a ticker, annual by default. Returns None on failure."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            stock = yf.Ticker(ticker)
            statement = stock.quarterly_balance_sheet if quarterly else stock.balance_sheet
            if statement is None or statement.empty:
                raise ExternalAPIError(f"No balance sheet data available for {ticker}.")
            return statement
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"Balance sheet fetch attempt {attempt}/{_MAX_RETRIES} failed for {ticker}: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    logger.error(f"Balance sheet fetch failed for {ticker} after {_MAX_RETRIES} attempts: {last_exc}")
    return None


def render_balance_sheet(ticker: str) -> None:
    """Render the Balance Sheet tab: an annual/quarterly toggle plus a formatted table."""
    render_section_header("Balance Sheet", icon="📋")

    period = st.radio("Period", ["Annual", "Quarterly"], horizontal=True, key="balance_sheet_period")
    statement = get_balance_sheet(ticker, quarterly=(period == "Quarterly"))

    if statement is None:
        st.info(f"Balance sheet data is not available for {ticker}.")
        return

    display_df = statement.loc[[row for row in _KEY_ROWS if row in statement.index]]
    display_df.columns = [col.strftime("%b %Y") if hasattr(col, "strftime") else str(col) for col in display_df.columns]
    st.dataframe(display_df.style.format(lambda v: f"{v:,.0f}" if pd.notna(v) else "--"), use_container_width=True)

    with st.expander("View full statement"):
        st.dataframe(statement, use_container_width=True)
