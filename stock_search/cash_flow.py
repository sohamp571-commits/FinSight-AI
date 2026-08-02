"""
stock_search/cash_flow.py

Purpose: Fetches and renders a company's Cash Flow Statement (annual
and quarterly) from yfinance, completing the three core financial
statements alongside income_statement.py and balance_sheet.py.
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
    "Operating Cash Flow",
    "Investing Cash Flow",
    "Financing Cash Flow",
    "Free Cash Flow",
    "Capital Expenditure",
    "End Cash Position",
]


@st.cache_data(ttl=3600, show_spinner=False)
def get_cash_flow(ticker: str, quarterly: bool = False) -> pd.DataFrame | None:
    """Fetch the cash flow statement for a ticker, annual by default. Returns None on failure."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            stock = yf.Ticker(ticker)
            statement = stock.quarterly_cashflow if quarterly else stock.cashflow
            if statement is None or statement.empty:
                raise ExternalAPIError(f"No cash flow data available for {ticker}.")
            return statement
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"Cash flow fetch attempt {attempt}/{_MAX_RETRIES} failed for {ticker}: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    logger.error(f"Cash flow fetch failed for {ticker} after {_MAX_RETRIES} attempts: {last_exc}")
    return None


def render_cash_flow(ticker: str) -> None:
    """Render the Cash Flow tab: an annual/quarterly toggle plus a formatted table."""
    render_section_header("Cash Flow Statement", icon="💵")

    period = st.radio("Period", ["Annual", "Quarterly"], horizontal=True, key="cash_flow_period")
    statement = get_cash_flow(ticker, quarterly=(period == "Quarterly"))

    if statement is None:
        st.info(f"Cash flow data is not available for {ticker}.")
        return

    display_df = statement.loc[[row for row in _KEY_ROWS if row in statement.index]]
    display_df.columns = [col.strftime("%b %Y") if hasattr(col, "strftime") else str(col) for col in display_df.columns]
    st.dataframe(display_df.style.format(lambda v: f"{v:,.0f}" if pd.notna(v) else "--"), use_container_width=True)

    with st.expander("View full statement"):
        st.dataframe(statement, use_container_width=True)
