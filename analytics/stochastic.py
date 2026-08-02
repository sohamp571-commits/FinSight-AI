"""
analytics/stochastic.py

Purpose: Implements the Stochastic Oscillator (%K and its %D signal
line) plus a dedicated Plotly panel with overbought (80) / oversold
(20) reference lines and a derived BUY/SELL/NEUTRAL signal.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.chart_helpers import CHART_CONFIG, apply_dark_theme

DEFAULT_K_PERIOD = 14
DEFAULT_D_PERIOD = 3
OVERBOUGHT_THRESHOLD = 80
OVERSOLD_THRESHOLD = 20


def calculate_stochastic(
    df: pd.DataFrame, k_period: int = DEFAULT_K_PERIOD, d_period: int = DEFAULT_D_PERIOD
) -> pd.DataFrame:
    """Return a DataFrame with columns: %K, %D."""
    lowest_low = df["Low"].rolling(window=k_period, min_periods=k_period).min()
    highest_high = df["High"].rolling(window=k_period, min_periods=k_period).max()

    range_ = (highest_high - lowest_low).replace(0, pd.NA)
    percent_k = ((df["Close"] - lowest_low) / range_) * 100
    percent_d = percent_k.rolling(window=d_period, min_periods=d_period).mean()

    return pd.DataFrame({"%K": percent_k.fillna(50), "%D": percent_d.fillna(50)})


def get_stochastic_signal(latest_row: pd.Series) -> str:
    """Return BUY (oversold), SELL (overbought), or NEUTRAL based on %K."""
    k_value = latest_row["%K"]
    if pd.isna(k_value):
        return "NEUTRAL"
    if k_value <= OVERSOLD_THRESHOLD:
        return "BUY"
    if k_value >= OVERBOUGHT_THRESHOLD:
        return "SELL"
    return "NEUTRAL"


def build_stochastic_chart(df: pd.DataFrame) -> go.Figure:
    """Build the Stochastic Oscillator chart with %K, %D, and reference bands."""
    stoch = calculate_stochastic(df)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=stoch["%K"], mode="lines", line=dict(color="#4F8BF9", width=2), name="%K"))
    fig.add_trace(go.Scatter(x=df.index, y=stoch["%D"], mode="lines", line=dict(color="#F59E0B", width=2), name="%D"))
    fig.add_hline(y=OVERBOUGHT_THRESHOLD, line_dash="dash", line_color="#EF4444", annotation_text="Overbought (80)")
    fig.add_hline(y=OVERSOLD_THRESHOLD, line_dash="dash", line_color="#22C55E", annotation_text="Oversold (20)")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(title=f"Stochastic Oscillator ({DEFAULT_K_PERIOD}, {DEFAULT_D_PERIOD})")
    return apply_dark_theme(fig, height=280, show_legend=True)


def render_stochastic_panel(df: pd.DataFrame) -> None:
    """Render the Stochastic Oscillator chart plus the current signal."""
    stoch = calculate_stochastic(df)
    latest_row = stoch.iloc[-1]
    signal = get_stochastic_signal(latest_row)
    signal_color = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "🟡"}[signal]

    st.plotly_chart(build_stochastic_chart(df), use_container_width=True, config=CHART_CONFIG, key="stochastic_chart")
    st.caption(f"%K: **{latest_row['%K']:.2f}** • %D: **{latest_row['%D']:.2f}**  {signal_color} Signal: **{signal}**")
