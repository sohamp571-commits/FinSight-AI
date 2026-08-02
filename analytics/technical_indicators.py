"""
analytics/technical_indicators.py

Purpose: A facade over every indicator module -- computes SMA/EMA/WMA,
RSI, MACD, Bollinger Bands, ATR, ADX, and Stochastic in one call and
returns their latest values as a flat dict. Used by
technical_analysis.py to render a single "All Indicators" reference
table without every page needing to import ten modules individually.
"""

import pandas as pd
import streamlit as st

from analytics.adx import calculate_adx
from analytics.atr import calculate_atr
from analytics.bollinger_bands import calculate_bollinger_bands
from analytics.macd import calculate_macd
from analytics.moving_average import calculate_ema, calculate_sma, calculate_wma
from analytics.rsi import calculate_rsi
from analytics.stochastic import calculate_stochastic


def compute_all_indicators(df: pd.DataFrame) -> dict[str, float | None]:
    """
    Compute the latest value of every implemented technical indicator
    for the given OHLCV DataFrame.

    Returns:
        A flat dict of {indicator_label: latest_value_or_None}.
    """
    close = df["Close"]

    def _last(series: pd.Series) -> float | None:
        if series is None or series.empty or pd.isna(series.iloc[-1]):
            return None
        return round(float(series.iloc[-1]), 2)

    macd_df = calculate_macd(close)
    bb_df = calculate_bollinger_bands(close)
    adx_df = calculate_adx(df)
    stoch_df = calculate_stochastic(df)

    return {
        "SMA (20)": _last(calculate_sma(close, 20)) if len(close) >= 20 else None,
        "SMA (50)": _last(calculate_sma(close, 50)) if len(close) >= 50 else None,
        "SMA (200)": _last(calculate_sma(close, 200)) if len(close) >= 200 else None,
        "EMA (12)": _last(calculate_ema(close, 12)) if len(close) >= 12 else None,
        "EMA (26)": _last(calculate_ema(close, 26)) if len(close) >= 26 else None,
        "WMA (20)": _last(calculate_wma(close, 20)) if len(close) >= 20 else None,
        "RSI (14)": _last(calculate_rsi(close)),
        "MACD": _last(macd_df["macd"]),
        "MACD Signal": _last(macd_df["signal"]),
        "Bollinger Upper": _last(bb_df["upper"]),
        "Bollinger Middle": _last(bb_df["middle"]),
        "Bollinger Lower": _last(bb_df["lower"]),
        "ATR (14)": _last(calculate_atr(df)),
        "ADX (14)": _last(adx_df["adx"]),
        "+DI": _last(adx_df["plus_di"]),
        "-DI": _last(adx_df["minus_di"]),
        "Stochastic %K": _last(stoch_df["%K"]),
        "Stochastic %D": _last(stoch_df["%D"]),
    }


def render_all_indicators_table(df: pd.DataFrame) -> None:
    """Render every computed indicator's latest value as a single reference table."""
    indicators = compute_all_indicators(df)
    rows = [{"Indicator": name, "Value": value if value is not None else "N/A"} for name, value in indicators.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
