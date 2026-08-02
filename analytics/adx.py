"""
analytics/adx.py

Purpose: Implements the Average Directional Index (ADX) along with its
component +DI/-DI lines, using Wilder's smoothing -- the standard
trend-strength (not direction) indicator. Reuses `atr.calculate_true_range`
rather than recomputing True Range.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.atr import calculate_true_range
from dashboard.chart_helpers import CHART_CONFIG, COLOR_NEGATIVE, COLOR_POSITIVE, apply_dark_theme

DEFAULT_PERIOD = 14

STRONG_TREND_THRESHOLD = 25
MODERATE_TREND_THRESHOLD = 20


def calculate_adx(df: pd.DataFrame, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Return a DataFrame with columns: plus_di, minus_di, adx."""
    high, low = df["High"], df["Low"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    true_range = calculate_true_range(df)
    smoothed_tr = true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    smoothed_plus_dm = plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    smoothed_minus_dm = minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    plus_di = 100 * (smoothed_plus_dm / smoothed_tr.replace(0, pd.NA))
    minus_di = 100 * (smoothed_minus_dm / smoothed_tr.replace(0, pd.NA))

    di_sum = (plus_di + minus_di).replace(0, pd.NA)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    return pd.DataFrame({"plus_di": plus_di.fillna(0), "minus_di": minus_di.fillna(0), "adx": adx.fillna(0)})


def get_trend_strength(latest_adx: float | None) -> str:
    """Classify trend strength per Wilder's original ADX thresholds."""
    if latest_adx is None or pd.isna(latest_adx):
        return "Unknown"
    if latest_adx >= STRONG_TREND_THRESHOLD:
        return "Strong Trend"
    if latest_adx >= MODERATE_TREND_THRESHOLD:
        return "Moderate Trend"
    return "Weak / No Trend"


def build_adx_chart(df: pd.DataFrame, period: int = DEFAULT_PERIOD) -> go.Figure:
    """Build the ADX chart with +DI and -DI overlay lines."""
    adx_df = calculate_adx(df, period)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=adx_df["adx"], mode="lines", line=dict(color="#F59E0B", width=2), name="ADX"))
    fig.add_trace(go.Scatter(x=df.index, y=adx_df["plus_di"], mode="lines", line=dict(color=COLOR_POSITIVE, width=1.5), name="+DI"))
    fig.add_trace(go.Scatter(x=df.index, y=adx_df["minus_di"], mode="lines", line=dict(color=COLOR_NEGATIVE, width=1.5), name="-DI"))
    fig.add_hline(y=STRONG_TREND_THRESHOLD, line_dash="dash", line_color="rgba(148,163,184,0.4)", annotation_text="Strong (25)")
    fig.update_layout(title=f"ADX / +DI / -DI ({period})")
    return apply_dark_theme(fig, height=280, show_legend=True)


def render_adx_panel(df: pd.DataFrame, period: int = DEFAULT_PERIOD) -> None:
    """Render the ADX chart plus the current trend-strength classification."""
    adx_df = calculate_adx(df, period)
    latest = adx_df.iloc[-1]
    strength = get_trend_strength(latest["adx"])
    direction = "Bullish" if latest["plus_di"] > latest["minus_di"] else "Bearish"

    st.plotly_chart(build_adx_chart(df, period), use_container_width=True, config=CHART_CONFIG, key="adx_chart")
    st.caption(f"ADX: **{latest['adx']:.2f}** • {strength} • Directional bias: **{direction}**")
