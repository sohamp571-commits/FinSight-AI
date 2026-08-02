"""
analytics/trend_analysis.py

Purpose: Synthesizes a single overall trend read -- direction
(Uptrend/Downtrend/Sideways) and strength (Strong/Moderate/Weak) --
by combining moving_average.py's price-vs-MA position with adx.py's
trend-strength classification, rather than each indicator being read
in isolation. This is what signal_generator.py and technical_analysis.py
use for the headline "Trend" readout.
"""

import pandas as pd
import streamlit as st

from analytics.adx import calculate_adx, get_trend_strength
from analytics.moving_average import calculate_sma


def analyze_trend(df: pd.DataFrame) -> dict[str, str | float]:
    """
    Determine overall trend direction and strength for a DataFrame.

    Returns:
        {"direction": str, "strength": str, "adx_value": float,
         "price": float, "sma_20": float, "sma_50": float}
    """
    close = df["Close"]
    latest_price = float(close.iloc[-1])

    sma_20 = calculate_sma(close, 20).iloc[-1]
    sma_50 = calculate_sma(close, 50).iloc[-1] if len(close) >= 50 else None

    adx_df = calculate_adx(df)
    latest_adx = float(adx_df["adx"].iloc[-1]) if not adx_df.empty else None
    strength = get_trend_strength(latest_adx)

    if sma_50 is not None and pd.notna(sma_20) and pd.notna(sma_50):
        if latest_price > sma_20 > sma_50:
            direction = "Uptrend"
        elif latest_price < sma_20 < sma_50:
            direction = "Downtrend"
        else:
            direction = "Sideways"
    elif pd.notna(sma_20):
        direction = "Uptrend" if latest_price > sma_20 else "Downtrend"
    else:
        direction = "Unknown"

    return {
        "direction": direction,
        "strength": strength,
        "adx_value": round(latest_adx, 2) if latest_adx is not None else None,
        "price": latest_price,
        "sma_20": round(float(sma_20), 2) if pd.notna(sma_20) else None,
        "sma_50": round(float(sma_50), 2) if sma_50 is not None and pd.notna(sma_50) else None,
    }


def render_trend_summary(df: pd.DataFrame) -> dict[str, str | float]:
    """Render the headline trend direction/strength summary and return the underlying data."""
    trend = analyze_trend(df)

    direction_icon = {"Uptrend": "📈", "Downtrend": "📉", "Sideways": "➡️", "Unknown": "❓"}[trend["direction"]]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Trend Direction", f"{direction_icon} {trend['direction']}")
    with col2:
        st.metric("Trend Strength", trend["strength"])
    with col3:
        st.metric("ADX Value", f"{trend['adx_value']:.2f}" if trend["adx_value"] is not None else "N/A")

    return trend
