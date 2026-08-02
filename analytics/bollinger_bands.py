"""
analytics/bollinger_bands.py

Purpose: Implements Bollinger Bands (middle SMA, upper/lower bands at
+/- N standard deviations) plus a dedicated overlay chart and a
price-position-based BUY/SELL/NEUTRAL signal. Reuses
`moving_average.calculate_sma`.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.moving_average import calculate_sma
from dashboard.chart_helpers import CHART_CONFIG, COLOR_ACCENT, apply_dark_theme

DEFAULT_WINDOW = 20
DEFAULT_NUM_STD = 2


def calculate_bollinger_bands(
    series: pd.Series, window: int = DEFAULT_WINDOW, num_std: float = DEFAULT_NUM_STD
) -> pd.DataFrame:
    """Return a DataFrame with columns: middle, upper, lower."""
    middle = calculate_sma(series, window)
    rolling_std = series.rolling(window=window, min_periods=window).std()
    upper = middle + (rolling_std * num_std)
    lower = middle - (rolling_std * num_std)
    return pd.DataFrame({"middle": middle, "upper": upper, "lower": lower})


def get_bollinger_signal(price: float, bands_row: pd.Series) -> str:
    """
    Return SELL if price is at/above the upper band (overbought/potential
    reversal), BUY if at/below the lower band, otherwise NEUTRAL.
    """
    if pd.isna(bands_row["upper"]) or pd.isna(bands_row["lower"]):
        return "NEUTRAL"
    if price >= bands_row["upper"]:
        return "SELL"
    if price <= bands_row["lower"]:
        return "BUY"
    return "NEUTRAL"


def build_bollinger_overlay(fig: go.Figure, df: pd.DataFrame) -> go.Figure:
    """Add Bollinger Band traces onto an existing figure (e.g. a candlestick chart)."""
    bands = calculate_bollinger_bands(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=bands["upper"], mode="lines", line=dict(color="rgba(148,163,184,0.5)", width=1), name="BB Upper"))
    fig.add_trace(go.Scatter(x=df.index, y=bands["middle"], mode="lines", line=dict(color=COLOR_ACCENT, width=1, dash="dot"), name="BB Middle"))
    fig.add_trace(
        go.Scatter(
            x=df.index, y=bands["lower"], mode="lines", line=dict(color="rgba(148,163,184,0.5)", width=1),
            name="BB Lower", fill="tonexty", fillcolor="rgba(79, 139, 249, 0.06)",
        )
    )
    return fig


def build_bollinger_chart(df: pd.DataFrame) -> go.Figure:
    """Build a standalone Bollinger Bands chart (close price + bands)."""
    fig = go.Figure(go.Scatter(x=df.index, y=df["Close"], mode="lines", line=dict(color=COLOR_ACCENT, width=2), name="Close"))
    fig = build_bollinger_overlay(fig, df)
    fig.update_layout(title="Bollinger Bands (20, 2)")
    return apply_dark_theme(fig, height=320, show_legend=True)


def render_bollinger_panel(df: pd.DataFrame) -> None:
    """Render the Bollinger Bands chart plus the current position-based signal."""
    bands = calculate_bollinger_bands(df["Close"])
    latest_price = float(df["Close"].iloc[-1])
    signal = get_bollinger_signal(latest_price, bands.iloc[-1])
    signal_color = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}[signal]

    st.plotly_chart(build_bollinger_chart(df), use_container_width=True, config=CHART_CONFIG, key="bollinger_chart")
    st.caption(f"{signal_color} Bollinger Band Signal: **{signal}**")
