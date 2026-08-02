"""
analytics/moving_average.py

Purpose: Implements Simple, Exponential, and Weighted Moving Averages
(SMA/EMA/WMA) as pure pandas functions -- reused as overlays on the
candlestick chart and as inputs to trend_analysis.py/signal_generator.py
-- plus a standalone render function showing current MA values and a
price-vs-MA bullish/bearish read.
"""

import numpy as np
import pandas as pd
import streamlit as st

DEFAULT_SMA_WINDOWS = (20, 50, 200)
DEFAULT_EMA_WINDOWS = (12, 26)


def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average: unweighted mean of the last `window` values."""
    return series.rolling(window=window, min_periods=window).mean()


def calculate_ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential Moving Average: more weight on recent values, via pandas' ewm."""
    return series.ewm(span=window, adjust=False, min_periods=window).mean()


def calculate_wma(series: pd.Series, window: int) -> pd.Series:
    """Weighted Moving Average: linearly increasing weights toward the most recent value."""
    weights = np.arange(1, window + 1)

    def _weighted(values: np.ndarray) -> float:
        return float(np.dot(values, weights) / weights.sum())

    return series.rolling(window=window, min_periods=window).apply(_weighted, raw=True)


def get_ma_crossover_signal(price: float, short_ma: float | None, long_ma: float | None) -> str:
    """
    Return a simple BUY/SELL/NEUTRAL read based on price position relative
    to a short and long moving average (a lightweight golden/death-cross proxy).
    """
    if short_ma is None or long_ma is None or pd.isna(short_ma) or pd.isna(long_ma):
        return "NEUTRAL"
    if price > short_ma > long_ma:
        return "BUY"
    if price < short_ma < long_ma:
        return "SELL"
    return "NEUTRAL"


def render_moving_average_panel(df: pd.DataFrame) -> None:
    """Render current SMA/EMA values and a plain-English crossover read."""
    close = df["Close"]
    latest_price = float(close.iloc[-1])

    sma_20 = calculate_sma(close, 20).iloc[-1]
    sma_50 = calculate_sma(close, 50).iloc[-1] if len(close) >= 50 else None
    ema_12 = calculate_ema(close, 12).iloc[-1]
    ema_26 = calculate_ema(close, 26).iloc[-1] if len(close) >= 26 else None

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("SMA (20)", f"{sma_20:,.2f}" if pd.notna(sma_20) else "N/A")
    with col2:
        st.metric("SMA (50)", f"{sma_50:,.2f}" if sma_50 is not None and pd.notna(sma_50) else "N/A")
    with col3:
        st.metric("EMA (12)", f"{ema_12:,.2f}" if pd.notna(ema_12) else "N/A")

    signal = get_ma_crossover_signal(latest_price, sma_20, sma_50)
    signal_color = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}[signal]
    st.caption(f"{signal_color} Price vs. Moving Averages: **{signal}**")
