"""
analytics/line_chart.py

Purpose: Builds an interactive line chart of a selectable OHLC field
(Close/Open/High/Low) with an optional moving-average overlay --
a simpler alternative view to the candlestick chart, useful for
multi-timeframe comparison and cleaner trend reading.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.moving_average import calculate_sma
from dashboard.chart_helpers import CHART_CONFIG, COLOR_ACCENT, apply_dark_theme

FIELD_OPTIONS = ["Close", "Open", "High", "Low"]


def build_line_chart(df: pd.DataFrame, ticker: str, field: str = "Close", show_sma: bool = True) -> go.Figure:
    """Build an interactive line chart of the selected price field, with an optional SMA(20) overlay."""
    fig = go.Figure(
        go.Scatter(x=df.index, y=df[field], mode="lines", line=dict(color=COLOR_ACCENT, width=2), name=field)
    )

    if show_sma and len(df) >= 20:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=calculate_sma(df[field], 20), mode="lines",
                line=dict(color="#F59E0B", width=1.5, dash="dot"), name="SMA 20",
            )
        )

    fig.update_layout(title=f"{ticker} — {field} Price")
    return apply_dark_theme(fig, height=380, show_legend=show_sma)


def render_line_chart_panel(df: pd.DataFrame, ticker: str) -> None:
    """Render the field selector, SMA toggle, and the resulting line chart."""
    col1, col2 = st.columns([3, 1])
    with col1:
        field = st.selectbox("Price Field", FIELD_OPTIONS, index=0, key="line_chart_field")
    with col2:
        show_sma = st.checkbox("Show SMA (20)", value=True, key="line_chart_sma_toggle")

    fig = build_line_chart(df, ticker, field, show_sma)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="line_chart")
