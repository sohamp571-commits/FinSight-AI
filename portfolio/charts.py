"""
portfolio/charts.py

Purpose: Every Plotly chart builder specific to the Portfolio module --
allocation pie, portfolio growth, daily performance, sector exposure,
and a risk gauge. Reuses `dashboard.chart_helpers.apply_dark_theme`
and the shared color palette, exactly like `machine_learning/visualization.py`
and `analytics/*.py` do for their own charts.
"""

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from dashboard.chart_helpers import COLOR_NEGATIVE, COLOR_POSITIVE, apply_dark_theme

_PALETTE = ["#4F8BF9", "#22C55E", "#F59E0B", "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#94A3B8"]


def build_allocation_pie_chart(weights: dict[str, float]) -> go.Figure:
    """Build a pie chart of per-ticker portfolio allocation."""
    if not weights:
        fig = go.Figure()
        fig.add_annotation(text="No holdings to display.", showarrow=False, font=dict(size=14))
        return apply_dark_theme(fig, height=360)

    labels = list(weights.keys())
    values = list(weights.values())

    fig = go.Figure(
        go.Pie(
            labels=labels, values=values, hole=0.45,
            marker=dict(colors=(_PALETTE * ((len(labels) // len(_PALETTE)) + 1))[: len(labels)]),
            textinfo="label+percent",
        )
    )
    fig.update_layout(title="Asset Allocation")
    return apply_dark_theme(fig, height=380, show_legend=True)


def build_sector_exposure_chart(sector_weights: dict[str, float]) -> go.Figure:
    """Build a horizontal bar chart of sector-level exposure."""
    if not sector_weights:
        fig = go.Figure()
        fig.add_annotation(text="No sector data to display.", showarrow=False, font=dict(size=14))
        return apply_dark_theme(fig, height=320)

    sorted_items = sorted(sector_weights.items(), key=lambda pair: pair[1])
    fig = go.Figure(
        go.Bar(
            x=[weight for _, weight in sorted_items],
            y=[sector for sector, _ in sorted_items],
            orientation="h",
            marker_color=_PALETTE[0],
            text=[f"{weight:.1f}%" for _, weight in sorted_items],
            textposition="outside",
        )
    )
    fig.update_layout(title="Sector Exposure", xaxis_title="Weight (%)")
    return apply_dark_theme(fig, height=max(320, 32 * len(sorted_items)))


def build_portfolio_growth_chart(transactions: list[dict[str, Any]]) -> go.Figure:
    """
    Build a cumulative invested-capital growth chart from transaction
    history -- a running total of net capital deployed over time
    (BUY adds, SELL subtracts), which is what's actually knowable from
    the transaction ledger without a full point-in-time valuation replay.
    """
    if not transactions:
        fig = go.Figure()
        fig.add_annotation(text="No transaction history yet.", showarrow=False, font=dict(size=14))
        return apply_dark_theme(fig, height=340)

    df = pd.DataFrame(transactions).sort_values("transaction_date")
    df["signed_amount"] = df.apply(lambda r: r["total_amount"] if r["transaction_type"] == "BUY" else -r["total_amount"], axis=1)
    df["cumulative_invested"] = df["signed_amount"].cumsum()

    fig = go.Figure(
        go.Scatter(
            x=df["transaction_date"], y=df["cumulative_invested"], mode="lines+markers",
            line=dict(color=_PALETTE[0], width=2), fill="tozeroy", fillcolor="rgba(79,139,249,0.08)",
            name="Net Invested Capital",
        )
    )
    fig.update_layout(title="Portfolio Growth (Net Invested Capital)")
    return apply_dark_theme(fig, height=360)


def build_daily_performance_chart(holdings: list[dict[str, Any]], quotes: dict[str, dict]) -> go.Figure:
    """Build a bar chart of each holding's today's gain/loss in currency terms."""
    if not holdings:
        fig = go.Figure()
        fig.add_annotation(text="No holdings to display.", showarrow=False, font=dict(size=14))
        return apply_dark_theme(fig, height=300)

    rows = []
    for holding in holdings:
        quote = quotes.get(holding["ticker_symbol"])
        if not quote:
            continue
        todays_change = (quote["price"] - quote["previous_close"]) * holding["quantity"]
        rows.append({"ticker": holding["ticker_symbol"], "change": todays_change})

    if not rows:
        fig = go.Figure()
        fig.add_annotation(text="Live price data unavailable.", showarrow=False, font=dict(size=14))
        return apply_dark_theme(fig, height=300)

    colors = [COLOR_POSITIVE if r["change"] >= 0 else COLOR_NEGATIVE for r in rows]
    fig = go.Figure(
        go.Bar(x=[r["ticker"] for r in rows], y=[r["change"] for r in rows], marker_color=colors)
    )
    fig.update_layout(title="Today's Performance by Holding")
    return apply_dark_theme(fig, height=300)


def build_risk_gauge(risk_score: float, risk_label: str) -> go.Figure:
    """Build a gauge chart visualizing the composite portfolio risk score (0-100)."""
    color = COLOR_POSITIVE if risk_score < 40 else ("#F59E0B" if risk_score < 70 else COLOR_NEGATIVE)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk_score,
            title={"text": f"Portfolio Risk — {risk_label}"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 40], "color": "rgba(34,197,94,0.15)"},
                    {"range": [40, 70], "color": "rgba(245,158,11,0.15)"},
                    {"range": [70, 100], "color": "rgba(239,68,68,0.15)"},
                ],
            },
        )
    )
    return apply_dark_theme(fig, height=260)
