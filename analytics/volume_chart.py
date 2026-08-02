"""
analytics/volume_chart.py

Purpose: Builds the Volume Analysis chart -- volume bars colored by
daily direction (reusing the same convention as
`dashboard.chart_helpers.build_volume_bar_chart`) plus a volume
moving-average overlay line, so unusually high/low volume relative to
the recent average is immediately visible.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, COLOR_NEGATIVE, COLOR_POSITIVE, apply_dark_theme

DEFAULT_VOLUME_MA_WINDOW = 20


def build_volume_chart(df: pd.DataFrame, ma_window: int = DEFAULT_VOLUME_MA_WINDOW) -> go.Figure:
    """Build a volume bar chart (green/red by daily direction) with a volume SMA overlay."""
    colors = [
        COLOR_POSITIVE if close >= open_ else COLOR_NEGATIVE
        for open_, close in zip(df["Open"], df["Close"])
    ]
    volume_ma = df["Volume"].rolling(window=ma_window, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=colors, name="Volume"))
    fig.add_trace(go.Scatter(x=df.index, y=volume_ma, mode="lines", line=dict(color="#F59E0B", width=2), name=f"Volume SMA({ma_window})"))
    fig.update_layout(title="Volume Analysis")
    return apply_dark_theme(fig, height=260, show_legend=True)


def get_volume_signal(df: pd.DataFrame, ma_window: int = DEFAULT_VOLUME_MA_WINDOW) -> str:
    """
    Return a plain-English volume read: current volume vs. its own
    recent average -- "High Volume", "Low Volume", or "Average Volume".
    """
    volume_ma = df["Volume"].rolling(window=ma_window, min_periods=1).mean()
    latest_volume = df["Volume"].iloc[-1]
    average_volume = volume_ma.iloc[-1]

    if average_volume == 0 or pd.isna(average_volume):
        return "Unknown"
    ratio = latest_volume / average_volume
    if ratio >= 1.5:
        return "High Volume"
    if ratio <= 0.5:
        return "Low Volume"
    return "Average Volume"


def render_volume_panel(df: pd.DataFrame) -> None:
    """Render the volume chart plus a plain-English volume read."""
    fig = build_volume_chart(df)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="volume_chart")

    signal = get_volume_signal(df)
    icon = {"High Volume": "🔥", "Low Volume": "🧊", "Average Volume": "➖", "Unknown": "❓"}[signal]
    st.caption(f"{icon} Volume Read: **{signal}**")
