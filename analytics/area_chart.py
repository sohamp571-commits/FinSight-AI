"""
analytics/area_chart.py

Purpose: Builds a gradient-filled area chart of closing price --
visually distinct from line_chart.py's plain line, colored green/red
based on the period's overall direction (first vs. last close), matching
the "Area Chart" requirement for multiple chart type options.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, COLOR_NEGATIVE, COLOR_POSITIVE, apply_dark_theme


def build_area_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Build a gradient-filled area chart of closing price, colored by overall period direction."""
    close = df["Close"]
    is_positive_period = float(close.iloc[-1]) >= float(close.iloc[0])
    line_color = COLOR_POSITIVE if is_positive_period else COLOR_NEGATIVE
    fill_color = "rgba(34, 197, 94, 0.12)" if is_positive_period else "rgba(239, 68, 68, 0.12)"

    fig = go.Figure(
        go.Scatter(
            x=df.index,
            y=close,
            mode="lines",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
            name="Close",
        )
    )
    fig.update_layout(title=f"{ticker} — Area Chart")
    fig.update_yaxes(rangemode="tozero" if close.min() > 0 else "normal")
    return apply_dark_theme(fig, height=380)


def render_area_chart_panel(df: pd.DataFrame, ticker: str) -> None:
    """Render the area chart panel."""
    fig = build_area_chart(df, ticker)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG, key="area_chart")
