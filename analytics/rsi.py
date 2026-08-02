"""
analytics/rsi.py

Purpose: Implements the Relative Strength Index (RSI) using Wilder's
smoothing method, plus a dedicated Plotly panel with overbought (70)
/ oversold (30) reference lines and a derived BUY/SELL/NEUTRAL signal.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, COLOR_ACCENT, apply_dark_theme

DEFAULT_RSI_PERIOD = 14
OVERBOUGHT_THRESHOLD = 70
OVERSOLD_THRESHOLD = 30


def calculate_rsi(series: pd.Series, period: int = DEFAULT_RSI_PERIOD) -> pd.Series:
    """
    Calculate RSI using Wilder's smoothing (an EMA with alpha = 1/period),
    the standard method used by TradingView and most charting platforms.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    relative_strength = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.fillna(50)  # neutral where undefined (e.g. no losses yet)


def get_rsi_signal(latest_rsi: float | None) -> str:
    """Return BUY (oversold, potential bounce), SELL (overbought), or NEUTRAL."""
    if latest_rsi is None or pd.isna(latest_rsi):
        return "NEUTRAL"
    if latest_rsi <= OVERSOLD_THRESHOLD:
        return "BUY"
    if latest_rsi >= OVERBOUGHT_THRESHOLD:
        return "SELL"
    return "NEUTRAL"


def build_rsi_chart(df: pd.DataFrame, period: int = DEFAULT_RSI_PERIOD) -> go.Figure:
    """Build the RSI line chart with overbought/oversold reference bands."""
    rsi_series = calculate_rsi(df["Close"], period)

    fig = go.Figure(go.Scatter(x=df.index, y=rsi_series, mode="lines", line=dict(color=COLOR_ACCENT, width=2), name="RSI"))
    fig.add_hline(y=OVERBOUGHT_THRESHOLD, line_dash="dash", line_color="#EF4444", annotation_text="Overbought (70)")
    fig.add_hline(y=OVERSOLD_THRESHOLD, line_dash="dash", line_color="#22C55E", annotation_text="Oversold (30)")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(title=f"RSI ({period})")
    return apply_dark_theme(fig, height=260)


def render_rsi_panel(df: pd.DataFrame, period: int = DEFAULT_RSI_PERIOD) -> None:
    """Render the RSI chart plus current value and signal."""
    rsi_series = calculate_rsi(df["Close"], period)
    latest_rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else None
    signal = get_rsi_signal(latest_rsi)
    signal_color = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}[signal]

    st.plotly_chart(build_rsi_chart(df, period), use_container_width=True, config=CHART_CONFIG, key="rsi_chart")
    st.caption(f"Current RSI: **{latest_rsi:.2f}**  {signal_color} Signal: **{signal}**" if latest_rsi is not None else "RSI unavailable.")
