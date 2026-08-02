"""
analytics/macd.py

Purpose: Implements the Moving Average Convergence Divergence (MACD)
indicator -- MACD line (EMA12 - EMA26), signal line (EMA9 of MACD),
and histogram -- plus a dedicated Plotly panel and a crossover-based
BUY/SELL/NEUTRAL signal. Reuses `moving_average.calculate_ema` rather
than re-implementing EMA.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.moving_average import calculate_ema
from dashboard.chart_helpers import CHART_CONFIG, COLOR_ACCENT, COLOR_NEGATIVE, COLOR_POSITIVE, apply_dark_theme

FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9


def calculate_macd(
    series: pd.Series, fast: int = FAST_PERIOD, slow: int = SLOW_PERIOD, signal: int = SIGNAL_PERIOD
) -> pd.DataFrame:
    """Return a DataFrame with columns: macd, signal, histogram."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": histogram})


def get_macd_signal(macd_df: pd.DataFrame) -> str:
    """
    Return BUY if MACD just crossed above the signal line, SELL if it
    just crossed below, otherwise NEUTRAL.
    """
    if len(macd_df) < 2:
        return "NEUTRAL"
    latest, previous = macd_df.iloc[-1], macd_df.iloc[-2]
    if pd.isna(latest["macd"]) or pd.isna(latest["signal"]):
        return "NEUTRAL"

    crossed_up = previous["macd"] <= previous["signal"] and latest["macd"] > latest["signal"]
    crossed_down = previous["macd"] >= previous["signal"] and latest["macd"] < latest["signal"]

    if crossed_up:
        return "BUY"
    if crossed_down:
        return "SELL"
    return "NEUTRAL"


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    """Build the MACD panel: MACD line, signal line, and a colored histogram."""
    macd_df = calculate_macd(df["Close"])
    histogram_colors = [COLOR_POSITIVE if v >= 0 else COLOR_NEGATIVE for v in macd_df["histogram"].fillna(0)]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=macd_df["histogram"], marker_color=histogram_colors, name="Histogram"))
    fig.add_trace(go.Scatter(x=df.index, y=macd_df["macd"], mode="lines", line=dict(color=COLOR_ACCENT, width=2), name="MACD"))
    fig.add_trace(go.Scatter(x=df.index, y=macd_df["signal"], mode="lines", line=dict(color="#F59E0B", width=2), name="Signal"))
    fig.update_layout(title="MACD (12, 26, 9)")
    return apply_dark_theme(fig, height=280, show_legend=True)


def render_macd_panel(df: pd.DataFrame) -> None:
    """Render the MACD chart plus the current crossover signal."""
    macd_df = calculate_macd(df["Close"])
    signal = get_macd_signal(macd_df)
    signal_color = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}[signal]

    st.plotly_chart(build_macd_chart(df), use_container_width=True, config=CHART_CONFIG, key="macd_chart")
    st.caption(f"{signal_color} MACD Signal: **{signal}**")
