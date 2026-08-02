"""
dashboard/market_data_service.py

Purpose: The single point of contact with `yfinance` for the entire
dashboard module. Every other dashboard file (market_indices.py,
top_gainers.py, market_heatmap.py, ...) calls into this module instead
of importing yfinance directly, so caching, retry behavior, and error
handling stay consistent in one place.

Design notes:
    - Uses `st.cache_data` for time-boxed caching (default 60s) so a
      dashboard rerun (every Streamlit interaction reruns the script)
      doesn't hammer Yahoo Finance's API.
    - Wraps every network call in a small retry loop, since yfinance
      occasionally raises transient errors (rate limiting, timeouts).
    - Never lets a single failed ticker crash the whole dashboard --
      failures are logged and surfaced as `None`/empty results so the
      UI can show a graceful "data unavailable" state per widget.
"""

import time
from datetime import datetime, time as dt_time
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf

from custom_exceptions import ExternalAPIError
from logging_config import logger

# ==========================================================
# Symbol Universe
# ==========================================================

MARKET_INDICES: dict[str, str] = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "NASDAQ": "^IXIC",
    "DOW JONES": "^DJI",
}

COMMODITIES_AND_OTHERS: dict[str, str] = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Bitcoin": "BTC-USD",
    "USD/INR": "USDINR=X",
}

ALL_OVERVIEW_SYMBOLS: dict[str, str] = {**MARKET_INDICES, **COMMODITIES_AND_OTHERS}

# A representative NSE large-cap universe used for gainers/losers/most-active/heatmap.
# (A full NIFTY 50 constituent list; kept here rather than constants.py since it is
# specific to this dashboard's data source, not a project-wide constant.)
NIFTY50_UNIVERSE: dict[str, str] = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "INFY.NS": "Infosys",
    "ITC.NS": "ITC",
    "SBIN.NS": "State Bank of India",
    "BHARTIARTL.NS": "Bharti Airtel",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "LT.NS": "Larsen & Toubro",
    "HINDUNILVR.NS": "Hindustan Unilever",
    "AXISBANK.NS": "Axis Bank",
    "ASIANPAINT.NS": "Asian Paints",
    "MARUTI.NS": "Maruti Suzuki",
    "SUNPHARMA.NS": "Sun Pharmaceutical",
    "TITAN.NS": "Titan Company",
    "BAJFINANCE.NS": "Bajaj Finance",
    "WIPRO.NS": "Wipro",
    "ULTRACEMCO.NS": "UltraTech Cement",
    "NESTLEIND.NS": "Nestle India",
    "HCLTECH.NS": "HCL Technologies",
    "ONGC.NS": "Oil & Natural Gas Corp",
    "NTPC.NS": "NTPC",
    "POWERGRID.NS": "Power Grid Corp",
    "TATAMOTORS.NS": "Tata Motors",
    "TATASTEEL.NS": "Tata Steel",
    "ADANIENT.NS": "Adani Enterprises",
    "JSWSTEEL.NS": "JSW Steel",
    "M&M.NS": "Mahindra & Mahindra",
    "TECHM.NS": "Tech Mahindra",
}

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 1.5
_CACHE_TTL_SECONDS = 60


def _retry(callable_fn, *args, **kwargs) -> Any:
    """Call `callable_fn` with simple exponential-backoff retry on failure."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return callable_fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - yfinance raises assorted exception types
            last_exc = exc
            logger.warning(f"Market data fetch attempt {attempt}/{_MAX_RETRIES} failed: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    logger.error(f"Market data fetch failed after {_MAX_RETRIES} attempts: {last_exc}")
    raise ExternalAPIError(f"Failed to fetch market data: {last_exc}")


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_quote(ticker: str) -> dict[str, Any] | None:
    """
    Fetch a single ticker's latest quote.

    Returns:
        {
            "ticker": str, "price": float, "previous_close": float,
            "change": float, "change_pct": float, "volume": int,
            "day_high": float, "day_low": float,
        }
        or None if the ticker could not be fetched after retries.
    """
    try:
        def _fetch() -> dict[str, Any]:
            info = yf.Ticker(ticker).fast_info
            price = float(info["last_price"])
            previous_close = float(info["previous_close"])
            change = price - previous_close
            change_pct = (change / previous_close * 100) if previous_close else 0.0
            return {
                "ticker": ticker,
                "price": price,
                "previous_close": previous_close,
                "change": change,
                "change_pct": change_pct,
                "volume": int(info.get("last_volume") or 0),
                "day_high": float(info.get("day_high") or price),
                "day_low": float(info.get("day_low") or price),
            }

        return _retry(_fetch)
    except ExternalAPIError as exc:
        logger.error(f"fetch_quote failed for {ticker}: {exc}")
        return None


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_quotes_bulk(tickers: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    """
    Fetch quotes for many tickers in as few network round-trips as
    possible using yfinance's batch download, falling back to
    per-ticker fetches for any symbol missing from the batch result.

    Args:
        tickers: A tuple (not list, so Streamlit can hash it for caching) of ticker symbols.

    Returns:
        {ticker: quote_dict, ...} -- tickers that failed entirely are omitted.
    """
    results: dict[str, dict[str, Any]] = {}

    def _batch_fetch() -> pd.DataFrame:
        return yf.download(
            tickers=list(tickers),
            period="2d",
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
        )

    try:
        data = _retry(_batch_fetch)
    except ExternalAPIError:
        data = None

    for ticker in tickers:
        try:
            if data is not None and not data.empty:
                ticker_frame = data[ticker] if len(tickers) > 1 else data
                closes = ticker_frame["Close"].dropna()
                volumes = ticker_frame["Volume"].dropna()
                if len(closes) >= 2:
                    price = float(closes.iloc[-1])
                    previous_close = float(closes.iloc[-2])
                    change = price - previous_close
                    change_pct = (change / previous_close * 100) if previous_close else 0.0
                    results[ticker] = {
                        "ticker": ticker,
                        "price": price,
                        "previous_close": previous_close,
                        "change": change,
                        "change_pct": change_pct,
                        "volume": int(volumes.iloc[-1]) if len(volumes) else 0,
                        "day_high": float(ticker_frame["High"].iloc[-1]),
                        "day_low": float(ticker_frame["Low"].iloc[-1]),
                    }
                    continue
        except (KeyError, IndexError, ValueError) as exc:
            logger.warning(f"Bulk quote parsing failed for {ticker}, falling back to single fetch: {exc}")

        single_quote = fetch_quote(ticker)
        if single_quote is not None:
            results[ticker] = single_quote

    return results


@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame | None:
    """Fetch OHLCV price history for a ticker (used by charts)."""
    try:
        def _fetch() -> pd.DataFrame:
            history = yf.Ticker(ticker).history(period=period, interval=interval)
            if history.empty:
                raise ExternalAPIError(f"No price history returned for {ticker}.")
            return history

        return _retry(_fetch)
    except ExternalAPIError as exc:
        logger.error(f"fetch_price_history failed for {ticker}: {exc}")
        return None


def get_market_status() -> dict[str, Any]:
    """
    Determine whether the NSE is currently in a regular trading
    session (Mon-Fri, 09:15-15:30 IST). Does not account for market
    holidays (would require a holiday calendar data source).

    Returns:
        {"is_open": bool, "label": str, "as_of": datetime}
    """
    now_ist = datetime.utcnow() + pd.Timedelta(hours=5, minutes=30)
    is_weekday = now_ist.weekday() < 5
    market_open = dt_time(9, 15)
    market_close = dt_time(15, 30)
    current_time = now_ist.time()

    is_open = is_weekday and market_open <= current_time <= market_close
    label = "Market Open" if is_open else "Market Closed"

    return {"is_open": is_open, "label": label, "as_of": now_ist}


def get_universe_quotes() -> dict[str, dict[str, Any]]:
    """Fetch quotes for the entire NIFTY-50-style universe (used by gainers/losers/heatmap)."""
    return fetch_quotes_bulk(tuple(NIFTY50_UNIVERSE.keys()))
