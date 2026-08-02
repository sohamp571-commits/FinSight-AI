"""
analytics/support_resistance.py

Purpose: Detects support and resistance price levels using a
fractal/pivot approach (a bar is a local high/low if it's more
extreme than `window` bars on either side), then clusters nearby
pivots into a small set of significant levels for charting and
signal generation.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, COLOR_NEGATIVE, COLOR_POSITIVE, apply_dark_theme

DEFAULT_PIVOT_WINDOW = 5
DEFAULT_CLUSTER_TOLERANCE_PCT = 1.5
MAX_LEVELS = 4


def _find_pivots(df: pd.DataFrame, window: int = DEFAULT_PIVOT_WINDOW) -> tuple[list[float], list[float]]:
    """Find local pivot highs (resistance candidates) and pivot lows (support candidates)."""
    highs, lows = df["High"], df["Low"]
    pivot_highs: list[float] = []
    pivot_lows: list[float] = []

    for i in range(window, len(df) - window):
        window_slice_high = highs.iloc[i - window : i + window + 1]
        window_slice_low = lows.iloc[i - window : i + window + 1]
        if highs.iloc[i] == window_slice_high.max():
            pivot_highs.append(float(highs.iloc[i]))
        if lows.iloc[i] == window_slice_low.min():
            pivot_lows.append(float(lows.iloc[i]))

    return pivot_highs, pivot_lows


def _cluster_levels(levels: list[float], tolerance_pct: float = DEFAULT_CLUSTER_TOLERANCE_PCT) -> list[float]:
    """Merge nearby pivot levels (within tolerance_pct of each other) into single representative levels."""
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters: list[list[float]] = [[sorted_levels[0]]]

    for level in sorted_levels[1:]:
        cluster_avg = sum(clusters[-1]) / len(clusters[-1])
        if abs(level - cluster_avg) / cluster_avg * 100 <= tolerance_pct:
            clusters[-1].append(level)
        else:
            clusters.append([level])

    # Rank clusters by how many pivots support them (more touches = more significant)
    clusters.sort(key=len, reverse=True)
    return [round(sum(cluster) / len(cluster), 2) for cluster in clusters[:MAX_LEVELS]]


def calculate_support_resistance(
    df: pd.DataFrame, window: int = DEFAULT_PIVOT_WINDOW
) -> dict[str, list[float]]:
    """
    Calculate clustered support and resistance levels for a DataFrame.

    Returns:
        {"support": [levels...], "resistance": [levels...]} (each up to MAX_LEVELS, ascending order)
    """
    pivot_highs, pivot_lows = _find_pivots(df, window)
    return {
        "support": sorted(_cluster_levels(pivot_lows)),
        "resistance": sorted(_cluster_levels(pivot_highs)),
    }


def build_support_resistance_chart(df: pd.DataFrame, levels: dict[str, list[float]]) -> go.Figure:
    """Build a close-price line chart annotated with horizontal support/resistance levels."""
    fig = go.Figure(go.Scatter(x=df.index, y=df["Close"], mode="lines", line=dict(color="#94A3B8", width=1.5), name="Close"))

    for level in levels["support"]:
        fig.add_hline(y=level, line_dash="dot", line_color=COLOR_POSITIVE, annotation_text=f"Support {level:,.2f}")
    for level in levels["resistance"]:
        fig.add_hline(y=level, line_dash="dot", line_color=COLOR_NEGATIVE, annotation_text=f"Resistance {level:,.2f}")

    fig.update_layout(title="Support & Resistance")
    return apply_dark_theme(fig, height=340)


def render_support_resistance_panel(df: pd.DataFrame) -> None:
    """Render the support/resistance chart plus a readable level list."""
    levels = calculate_support_resistance(df)

    if not levels["support"] and not levels["resistance"]:
        st.info("Not enough price history to identify clear support/resistance levels for this timeframe.")
        return

    st.plotly_chart(build_support_resistance_chart(df, levels), use_container_width=True, config=CHART_CONFIG, key="sr_chart")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Support Levels**")
        st.write(", ".join(f"{lvl:,.2f}" for lvl in levels["support"]) or "None detected")
    with col2:
        st.markdown("**Resistance Levels**")
        st.write(", ".join(f"{lvl:,.2f}" for lvl in levels["resistance"]) or "None detected")
