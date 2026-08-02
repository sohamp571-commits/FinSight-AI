"""
stock_search/historical_data.py

Purpose: Lets the user select a historical time range (1M/3M/6M/1Y/3Y/
5Y/Max), fetches OHLCV data via yfinance (with caching + retry),
renders an interactive candlestick + volume chart using the Phase 4
`chart_helpers` module, and offers a CSV export of the underlying data.
"""

import time

import pandas as pd
import streamlit as st
import yfinance as yf

from custom_exceptions import ExternalAPIError
from dashboard.chart_helpers import CHART_CONFIG, build_candlestick_chart, build_volume_bar_chart
from dashboard.dashboard_layout import render_section_header
from logging_config import logger

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 1.5

_PERIOD_OPTIONS: dict[str, str] = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "3 Years": "3y",
    "5 Years": "5y",
    "Maximum": "max",
}


@st.cache_data(ttl=900, show_spinner=False)
def get_historical_data(ticker: str, period: str) -> pd.DataFrame | None:
    """Fetch OHLCV history for a ticker over the given yfinance period string."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            history = yf.Ticker(ticker).history(period=period)
            if history.empty:
                raise ExternalAPIError(f"No historical data available for {ticker} over {period}.")
            return history
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"Historical data fetch attempt {attempt}/{_MAX_RETRIES} failed for {ticker}: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    logger.error(f"Historical data fetch failed for {ticker} after {_MAX_RETRIES} attempts: {last_exc}")
    return None


def render_historical_data(ticker: str) -> None:
    """Render the Historical Data tab: period selector, candlestick+volume chart, CSV export."""
    render_section_header("Historical Data", icon="🕰️")

    period_label = st.select_slider("Time Range", options=list(_PERIOD_OPTIONS.keys()), value="1 Year")
    period = _PERIOD_OPTIONS[period_label]

    with st.spinner(f"Loading {period_label.lower()} of price history for {ticker}..."):
        history = get_historical_data(ticker, period)

    if history is None:
        st.info(f"Historical data is not available for {ticker} over the selected range.")
        return

    price_fig = build_candlestick_chart(history, title=f"{ticker} — {period_label}")
    st.plotly_chart(price_fig, use_container_width=True, config=CHART_CONFIG, key=f"hist_price_{ticker}_{period}")

    volume_fig = build_volume_bar_chart(history)
    st.plotly_chart(volume_fig, use_container_width=True, config=CHART_CONFIG, key=f"hist_volume_{ticker}_{period}")

    csv_data = history.to_csv().encode("utf-8")
    st.download_button(
        label="⬇️ Export to CSV",
        data=csv_data,
        file_name=f"{ticker.replace('.', '_')}_{period}_history.csv",
        mime="text/csv",
        use_container_width=True,
    )
