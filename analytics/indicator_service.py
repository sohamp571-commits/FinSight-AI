"""
analytics/indicator_service.py

Purpose: The single data-access point for the Technical Analysis
module. Fetches multi-timeframe OHLCV data from yfinance (own
cache/retry, following the exact pattern already used by
`stock_search/historical_data.py` and every other data-fetching module
in this project) and exposes the timeframe options used throughout
`analytics/`. Every indicator/chart module receives a pandas DataFrame
from here rather than calling yfinance directly.
"""

import time

import pandas as pd
import streamlit as st
import yfinance as yf

from custom_exceptions import ExternalAPIError
from logging_config import logger

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 1.5

# label -> (yfinance period, yfinance interval)
TIMEFRAME_OPTIONS: dict[str, tuple[str, str]] = {
    "1 Day": ("1d", "5m"),
    "5 Day": ("5d", "15m"),
    "1 Month": ("1mo", "1d"),
    "3 Month": ("3mo", "1d"),
    "6 Month": ("6mo", "1d"),
    "1 Year": ("1y", "1d"),
    "5 Year": ("5y", "1wk"),
    "Maximum": ("max", "1mo"),
}

DEFAULT_TIMEFRAME = "6 Month"


@st.cache_data(ttl=300, show_spinner=False)
def get_ohlcv(ticker: str, timeframe_label: str) -> pd.DataFrame | None:
    """
    Fetch OHLCV data for a ticker at the given timeframe label (a key
    of TIMEFRAME_OPTIONS). Returns None if the data can't be fetched
    or is too short to be useful for indicator calculations.
    """
    if timeframe_label not in TIMEFRAME_OPTIONS:
        logger.error(f"Unknown timeframe label requested: {timeframe_label}")
        return None

    period, interval = TIMEFRAME_OPTIONS[timeframe_label]
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            history = yf.Ticker(ticker).history(period=period, interval=interval)
            if history.empty:
                raise ExternalAPIError(f"No OHLCV data available for {ticker} ({timeframe_label}).")
            history = history.dropna(subset=["Close"])
            return history
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"OHLCV fetch attempt {attempt}/{_MAX_RETRIES} failed for {ticker}: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)

    logger.error(f"OHLCV fetch failed for {ticker} after {_MAX_RETRIES} attempts: {last_exc}")
    return None


def has_sufficient_data(df: pd.DataFrame | None, minimum_bars: int = 30) -> bool:
    """Check whether a DataFrame has enough bars for meaningful indicator calculations."""
    return df is not None and len(df) >= minimum_bars
