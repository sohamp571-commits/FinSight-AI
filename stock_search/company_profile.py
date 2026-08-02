"""
stock_search/company_profile.py

Purpose: Fetches and renders a company's identity/profile information
-- name, sector, industry, CEO, website, market cap, employees,
country, exchange, currency, description, and business summary.
`get_company_info()` is the shared, cached fetch reused by
stock_statistics.py, valuation_metrics.py, and stock_comparison.py.
"""

import time
from typing import Any

import streamlit as st
import yfinance as yf

from custom_exceptions import ExternalAPIError
from dashboard.dashboard_layout import render_section_header
from helper import format_currency
from logging_config import logger

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 1.5


@st.cache_data(ttl=3600, show_spinner=False)
def get_company_info(ticker: str) -> dict[str, Any] | None:
    """Fetch the full yfinance `.info` dict for a ticker, with retry. Returns None on failure."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            info = yf.Ticker(ticker).info
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                raise ExternalAPIError(f"No profile data available for {ticker}.")
            return info
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"Company info fetch attempt {attempt}/{_MAX_RETRIES} failed for {ticker}: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    logger.error(f"Company info fetch failed for {ticker} after {_MAX_RETRIES} attempts: {last_exc}")
    return None


def _get_ceo_name(info: dict[str, Any]) -> str:
    """Extract the CEO's name from yfinance's officers list, if present."""
    for officer in info.get("companyOfficers", []) or []:
        title = (officer.get("title") or "").lower()
        if "chief executive" in title or title == "ceo":
            return officer.get("name", "N/A")
    return "N/A"


def render_company_profile(ticker: str) -> None:
    """Render the Company Profile section: identity fields + business summary."""
    info = get_company_info(ticker)
    if info is None:
        st.error(f"Could not load profile information for '{ticker}'. Please check the ticker symbol.")
        return

    company_name = info.get("longName") or info.get("shortName") or ticker
    render_section_header(company_name, subtitle=f"{ticker} • {info.get('exchange', 'N/A')}", icon="🏢")

    market_cap = info.get("marketCap")
    market_cap_display = format_currency(market_cap, "₹" if ".NS" in ticker or ".BO" in ticker else "$") if market_cap else "N/A"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Sector:** {info.get('sector', 'N/A')}")
        st.markdown(f"**Industry:** {info.get('industry', 'N/A')}")
        st.markdown(f"**Country:** {info.get('country', 'N/A')}")
    with col2:
        st.markdown(f"**CEO:** {_get_ceo_name(info)}")
        st.markdown(f"**Employees:** {info.get('fullTimeEmployees', 'N/A'):,}" if info.get("fullTimeEmployees") else "**Employees:** N/A")
        st.markdown(f"**Currency:** {info.get('currency', 'N/A')}")
    with col3:
        st.markdown(f"**Market Cap:** {market_cap_display}")
        website = info.get("website")
        st.markdown(f"**Website:** [{website}]({website})" if website else "**Website:** N/A")
        st.markdown(f"**Exchange:** {info.get('exchange', 'N/A')}")

    summary = info.get("longBusinessSummary")
    if summary:
        with st.expander("Business Summary", expanded=False):
            st.write(summary)
