"""
analytics/candlestick_chart.py

Purpose: Builds the primary interactive candlestick chart for the
Technical Analysis module, with selectable overlays (SMA, EMA,
Bollinger Bands) drawn directly on top of price. Reuses
`dashboard.chart_helpers.apply_dark_theme` for consistent styling and
`bollinger_bands.build_bollinger_overlay` rather than duplicating that
logic.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.bollinger_bands import build_bollinger_overlay
from analytics.moving_average import calculate_ema, calculate_sma
from dashboard.chart_helpers import CHART_CONFIG, COLOR_NEGATIVE, COLOR_POSITIVE, apply_dark_theme

OVERLAY_OPTIONS = ["SMA 20", "SMA 50", "EMA 12", "EMA 26", "Bollinger Bands"]


def build_candlestick_chart(df: pd.DataFrame, ticker: str, overlays: list[str] | None = None) -> go.Figure:
    """
    Build an interactive OHLC candlestick chart (zoom/pan/hover/fullscreen
    all come from Plotly's default toolbar + rangeslider) with any
    requested overlay indicators drawn on top.
    """
    overlays = overlays or []

    fig = go.Figure(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color=COLOR_POSITIVE,
            decreasing_line_color=COLOR_NEGATIVE,
            name=ticker,
        )
    )

    if "SMA 20" in overlays and len(df) >= 20:
        fig.add_trace(go.Scatter(x=df.index, y=calculate_sma(df["Close"], 20), mode="lines", line=dict(color="#4F8BF9", width=1.5), name="SMA 20"))
    if "SMA 50" in overlays and len(df) >= 50:
        fig.add_trace(go.Scatter(x=df.index, y=calculate_sma(df["Close"], 50), mode="lines", line=dict(color="#F59E0B", width=1.5), name="SMA 50"))
    if "EMA 12" in overlays and len(df) >= 12:
        fig.add_trace(go.Scatter(x=df.index, y=calculate_ema(df["Close"], 12), mode="lines", line=dict(color="#A78BFA", width=1.5), name="EMA 12"))
    if "EMA 26" in overlays and len(df) >= 26:
        fig.add_trace(go.Scatter(x=df.index, y=calculate_ema(df["Close"], 26), mode="lines", line=dict(color="#F472B6", width=1.5), name="EMA 26"))
    if "Bollinger Bands" in overlays and len(df) >= 20:
        fig = build_bollinger_overlay(fig, df)

    fig.update_layout(title=f"{ticker} — Price Chart", xaxis_rangeslider_visible=True)
    return apply_dark_theme(fig, height=480, show_legend=bool(overlays))


def render_candlestick_panel(df: pd.DataFrame, ticker: str) -> list[str]:
    """
    Render the overlay selector plus the candlestick chart. Returns the
    selected overlays so the caller (technical_analysis.py) can reuse
    the same selection elsewhere if needed.
    """
    overlays = st.multiselect(
        "Chart Overlays", options=OVERLAY_OPTIONS, default=["SMA 20", "SMA 50"], key="candlestick_overlays"
    )
    fig = build_candlestick_chart(df, ticker, overlays)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="candlestick_chart")
    return overlays
