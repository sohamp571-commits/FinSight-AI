"""
statistics/data_preparation.py

Purpose: Bridges FinSight AI's existing market-data layer to
`statistics/hypothesis_tests.py`. Deliberately reuses the project's
existing, already-cached data-fetching functions instead of calling
yfinance directly:

    - `stock_search.historical_data.get_historical_data` for OHLCV
      history (same function the Historical Data tab already uses).
    - `analytics.rsi.calculate_rsi` / `get_rsi_signal` for the RSI
      signal used in the Chi-square test (the same indicator already
      shown on the Technical Analysis page).

This module contains no Streamlit calls and no statistics -- it only
shapes data.
"""

import pandas as pd

from analytics.rsi import calculate_rsi, get_rsi_signal
from custom_exceptions import DataProcessingError
from logging_config import logger
from stock_search.historical_data import get_historical_data


def get_daily_returns(ticker: str, period: str) -> pd.Series:
    """
    Fetch OHLCV history for `ticker` over `period` (a yfinance period
    string, e.g. "6mo", "1y") and return its daily percentage returns
    on the closing price, indexed by date.

    Raises:
        DataProcessingError: if no historical data is available for
            the ticker/period.
    """
    history = get_historical_data(ticker, period)
    if history is None or history.empty:
        raise DataProcessingError(f"No historical price data is available for {ticker} over the selected period.")

    returns = history["Close"].pct_change().dropna()
    returns.name = ticker
    return returns


def get_bullish_bearish_returns(ticker: str, period: str, sma_window: int = 20) -> tuple[pd.Series, pd.Series]:
    """
    Split `ticker`'s daily returns into a "bullish" group (days where
    the closing price was above its `sma_window`-day SMA) and a
    "bearish" group (days it was below), for the "bullish vs bearish
    trading periods" T-test variant.

    Returns:
        (bullish_returns, bearish_returns) -- two independent samples
        of daily returns.

    Raises:
        DataProcessingError: if no historical data is available.
    """
    history = get_historical_data(ticker, period)
    if history is None or history.empty:
        raise DataProcessingError(f"No historical price data is available for {ticker} over the selected period.")

    close = history["Close"]
    sma = close.rolling(window=sma_window, min_periods=sma_window).mean()
    daily_returns = close.pct_change()

    frame = pd.DataFrame({"close": close, "sma": sma, "return": daily_returns}).dropna()
    bullish_returns = frame.loc[frame["close"] > frame["sma"], "return"]
    bearish_returns = frame.loc[frame["close"] <= frame["sma"], "return"]
    return bullish_returns, bearish_returns


def get_rsi_signal_vs_next_day_movement(ticker: str, period: str, rsi_period: int = 14) -> pd.DataFrame:
    """
    Build the categorical dataset for the Chi-square test: for every
    trading day (except the last, which has no "next day" yet),
    compute FinSight AI's existing RSI-based BUY/SELL/NEUTRAL signal
    for that day and the *actual* direction the price moved on the
    following day.

    This is the same logic `analytics/rsi.py::get_rsi_signal` already
    uses for the latest bar on the Technical Analysis page, applied
    across the whole history instead of just the most recent value.

    Returns:
        A DataFrame with two columns: "RSI Signal" (BUY/SELL/NEUTRAL)
        and "Next-Day Movement" (UP/DOWN), one row per trading day.

    Raises:
        DataProcessingError: if no historical data is available.
    """
    history = get_historical_data(ticker, period)
    if history is None or history.empty:
        raise DataProcessingError(f"No historical price data is available for {ticker} over the selected period.")

    close = history["Close"]
    rsi_series = calculate_rsi(close, rsi_period)
    signals = rsi_series.apply(lambda value: get_rsi_signal(value))

    # Next day's actual direction relative to today's close.
    next_day_change = close.shift(-1) - close
    movement = next_day_change.apply(lambda delta: "UP" if delta > 0 else ("DOWN" if delta < 0 else None))

    frame = pd.DataFrame({"RSI Signal": signals, "Next-Day Movement": movement})
    # Drop the last row (no next day yet) and any flat (unchanged) days,
    # which don't cleanly belong to either category.
    frame = frame.iloc[:-1].dropna()

    logger.info(f"Prepared RSI-signal-vs-movement dataset for {ticker} ({period}): {len(frame)} rows.")
    return frame