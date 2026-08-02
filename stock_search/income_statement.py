"""
stock_search/income_statement.py

Purpose: Fetches and renders a company's Income Statement (annual and
quarterly) from yfinance. Provides `get_income_statement()` as a
reusable data function (consumed by fundamental_analysis.py and
stock_comparison.py for ratio calculations) plus `render_income_statement()`
for the standalone Streamlit view.
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

_KEY_ROWS = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income", "EBITDA", "Diluted EPS"]


@st.cache_data(ttl=3600, show_spinner=False)
def get_income_statement(ticker: str, quarterly: bool = False) -> pd.DataFrame | None:
    """Fetch the income statement for a ticker, annual by default. Returns None on failure."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            stock = yf.Ticker(ticker)
            statement = stock.quarterly_income_stmt if quarterly else stock.income_stmt
            if statement is None or statement.empty:
                raise ExternalAPIError(f"No income statement data available for {ticker}.")
            return statement
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"Income statement fetch attempt {attempt}/{_MAX_RETRIES} failed for {ticker}: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    logger.error(f"Income statement fetch failed for {ticker} after {_MAX_RETRIES} attempts: {last_exc}")
    return None


def render_income_statement(ticker: str) -> None:
    """Render the Income Statement tab: an annual/quarterly toggle plus a formatted table."""
    render_section_header("Income Statement", icon="🧾")

    period = st.radio("Period", ["Annual", "Quarterly"], horizontal=True, key="income_statement_period")
    statement = get_income_statement(ticker, quarterly=(period == "Quarterly"))

    if statement is None:
        st.info(f"Income statement data is not available for {ticker}.")
        return

    display_df = statement.loc[[row for row in _KEY_ROWS if row in statement.index]]
    display_df.columns = [col.strftime("%b %Y") if hasattr(col, "strftime") else str(col) for col in display_df.columns]
    st.dataframe(display_df.style.format(lambda v: f"{v:,.0f}" if pd.notna(v) else "--"), use_container_width=True)

    with st.expander("View full statement"):
        st.dataframe(statement, use_container_width=True)
