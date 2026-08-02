"""
dashboard/chart_helpers.py

Purpose: Reusable Plotly chart-building functions shared across the
dashboard module, so every chart (sparklines on KPI cards, price
history, the market heatmap) has consistent styling, interactivity
(zoom/hover/fullscreen via Plotly's default toolbar), and dark-theme
support instead of each file hand-rolling its own `go.Figure`.
"""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Professional dark-friendly color palette shared across every chart.
COLOR_POSITIVE = "#22C55E"
COLOR_NEGATIVE = "#EF4444"
COLOR_NEUTRAL = "#94A3B8"
COLOR_ACCENT = "#4F8BF9"

CHART_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToAdd": ["drawline", "eraseshape"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def apply_dark_theme(fig: go.Figure, height: int = 320, show_legend: bool = False) -> go.Figure:
    """Apply a consistent dark, transparent-background theme to any Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color="#E2E8F0"),
        margin=dict(l=10, r=10, t=30, b=10),
        height=height,
        showlegend=show_legend,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.15)", zeroline=False)
    return fig


def build_sparkline(prices: list[float], change_positive: bool = True) -> go.Figure:
    """Build a minimal sparkline (no axes/labels) for KPI cards, colored by trend direction."""
    color = COLOR_POSITIVE if change_positive else COLOR_NEGATIVE
    fig = go.Figure(
        go.Scatter(
            y=prices,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=color.replace(")", ", 0.08)").replace("rgb", "rgba") if "rgb" in color else color + "14",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=60,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def build_price_line_chart(history: pd.DataFrame, title: str = "") -> go.Figure:
    """Build an interactive line chart of closing price over time (zoom/hover enabled by default)."""
    fig = go.Figure(
        go.Scatter(
            x=history.index,
            y=history["Close"],
            mode="lines",
            line=dict(color=COLOR_ACCENT, width=2),
            fill="tozeroy",
            fillcolor="rgba(79, 139, 249, 0.10)",
            name="Close",
        )
    )
    fig.update_layout(title=title, xaxis_title=None, yaxis_title="Price")
    return apply_dark_theme(fig, height=380)


def build_candlestick_chart(history: pd.DataFrame, title: str = "") -> go.Figure:
    """Build an interactive OHLC candlestick chart with a range slider."""
    fig = go.Figure(
        go.Candlestick(
            x=history.index,
            open=history["Open"],
            high=history["High"],
            low=history["Low"],
            close=history["Close"],
            increasing_line_color=COLOR_POSITIVE,
            decreasing_line_color=COLOR_NEGATIVE,
            name="Price",
        )
    )
    fig.update_layout(title=title, xaxis_rangeslider_visible=True)
    return apply_dark_theme(fig, height=420)


def build_volume_bar_chart(history: pd.DataFrame, title: str = "Volume") -> go.Figure:
    """Build a volume bar chart, colored green/red based on daily price direction."""
    colors = [
        COLOR_POSITIVE if close >= open_ else COLOR_NEGATIVE
        for open_, close in zip(history["Open"], history["Close"])
    ]
    fig = go.Figure(go.Bar(x=history.index, y=history["Volume"], marker_color=colors, name="Volume"))
    fig.update_layout(title=title)
    return apply_dark_theme(fig, height=220)


def build_market_heatmap(rows: list[dict[str, Any]]) -> go.Figure:
    """
    Build a Yahoo-Finance-style treemap heatmap: tile size = |change %|
    magnitude (via absolute value), tile color = signed change % on a
    red-to-green diverging scale.

    Args:
        rows: list of {"ticker": str, "name": str, "change_pct": float, "price": float}
    """
    if not rows:
        fig = go.Figure()
        fig.add_annotation(text="No market data available", showarrow=False, font=dict(size=16))
        return apply_dark_theme(fig, height=420)

    df = pd.DataFrame(rows)
    df["abs_change"] = df["change_pct"].abs().clip(lower=0.1)
    df["label"] = df.apply(
        lambda r: f"{r['ticker'].replace('.NS', '')}<br>{r['change_pct']:+.2f}%", axis=1
    )

    fig = px.treemap(
        df,
        path=[px.Constant("Market"), "label"],
        values="abs_change",
        color="change_pct",
        color_continuous_scale=["#7F1D1D", "#EF4444", "#334155", "#22C55E", "#14532D"],
        color_continuous_midpoint=0,
        hover_data={"price": ":.2f", "change_pct": ":.2f", "abs_change": False},
    )
    fig.update_traces(
        textposition="middle center",
        textfont=dict(size=13, color="white"),
        marker=dict(line=dict(width=1, color="#0E1117")),
    )
    fig.update_layout(coloraxis_showscale=False)
    return apply_dark_theme(fig, height=460)
