"""
analytics/atr.py

Purpose: Implements the Average True Range (ATR) -- a volatility (not
direction) indicator -- using Wilder's smoothing, plus a chart and a
plain-English volatility-regime read (relative to the ticker's own
recent history, since ATR has no universal threshold).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, COLOR_ACCENT, apply_dark_theme

DEFAULT_PERIOD = 14


def calculate_true_range(df: pd.DataFrame) -> pd.Series:
    """Calculate the True Range series: max of (high-low, |high-prevclose|, |low-prevclose|)."""
    previous_close = df["Close"].shift(1)
    high_low = df["High"] - df["Low"]
    high_prev_close = (df["High"] - previous_close).abs()
    low_prev_close = (df["Low"] - previous_close).abs()
    return pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)


def calculate_atr(df: pd.DataFrame, period: int = DEFAULT_PERIOD) -> pd.Series:
    """Calculate ATR via Wilder's smoothing (EMA with alpha = 1/period) of the True Range."""
    true_range = calculate_true_range(df)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def get_volatility_regime(atr_series: pd.Series) -> str:
    """
    Classify current volatility relative to its own recent history
    (ATR has no fixed universal threshold, unlike RSI/Stochastic).
    """
    if len(atr_series.dropna()) < DEFAULT_PERIOD * 2:
        return "Insufficient Data"

    latest_atr = atr_series.iloc[-1]
    historical_avg = atr_series.dropna().mean()
    if pd.isna(latest_atr) or historical_avg == 0:
        return "Insufficient Data"

    ratio = latest_atr / historical_avg
    if ratio >= 1.3:
        return "High Volatility"
    if ratio <= 0.7:
        return "Low Volatility"
    return "Normal Volatility"


def build_atr_chart(df: pd.DataFrame, period: int = DEFAULT_PERIOD) -> go.Figure:
    """Build the ATR line chart."""
    atr_series = calculate_atr(df, period)
    fig = go.Figure(go.Scatter(x=df.index, y=atr_series, mode="lines", line=dict(color=COLOR_ACCENT, width=2), fill="tozeroy", fillcolor="rgba(79,139,249,0.08)", name="ATR"))
    fig.update_layout(title=f"Average True Range ({period})")
    return apply_dark_theme(fig, height=240)


def render_atr_panel(df: pd.DataFrame, period: int = DEFAULT_PERIOD) -> None:
    """Render the ATR chart plus the current value and volatility regime read."""
    atr_series = calculate_atr(df, period)
    latest_atr = atr_series.iloc[-1] if not atr_series.empty else None
    regime = get_volatility_regime(atr_series)

    st.plotly_chart(build_atr_chart(df, period), use_container_width=True, config=CHART_CONFIG, key="atr_chart")
    if latest_atr is not None and pd.notna(latest_atr):
        st.caption(f"Current ATR: **{latest_atr:.2f}** • Volatility Regime: **{regime}**")
    else:
        st.caption("ATR unavailable for the current timeframe.")
