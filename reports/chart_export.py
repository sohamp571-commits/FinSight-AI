"""
reports/chart_export.py

Purpose: Renders static PNG images for embedding in the PDF report.
Deliberately does NOT recompute anything -- every function here takes
the exact same data shapes `portfolio/charts.py`'s Plotly builders
already take (weights dicts, sector dicts, transaction lists, risk
scores), just rendered with matplotlib instead of Plotly.

Why matplotlib instead of exporting the existing Plotly figures
directly: Plotly's `fig.to_image()` requires the `kaleido` package,
which is not in this project's `requirements.txt` and isn't installed
in every environment. matplotlib is already a Phase 1 dependency, so
using it here avoids adding a new dependency just for PDF export while
still visualizing the identical, already-calculated numbers.
"""

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless backend -- no display server available/needed
import matplotlib.pyplot as plt
import pandas as pd

_POSITIVE_COLOR = "#22C55E"
_NEGATIVE_COLOR = "#EF4444"
_ACCENT_COLOR = "#4F8BF9"
_PALETTE = ["#4F8BF9", "#22C55E", "#F59E0B", "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#94A3B8"]


def _figure_to_png_bytes(fig: plt.Figure) -> bytes:
    """Render a matplotlib figure to PNG bytes and close it to free memory."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()


def render_allocation_pie_image(weights: dict[str, float]) -> bytes | None:
    """Render the asset allocation pie chart as a PNG (same weights allocation_analysis.py already computed)."""
    if not weights:
        return None
    fig, ax = plt.subplots(figsize=(5, 4))
    colors = (_PALETTE * ((len(weights) // len(_PALETTE)) + 1))[: len(weights)]
    ax.pie(list(weights.values()), labels=list(weights.keys()), autopct="%1.1f%%", colors=colors, startangle=90)
    ax.set_title("Asset Allocation")
    return _figure_to_png_bytes(fig)


def render_sector_bar_image(sector_weights: dict[str, float]) -> bytes | None:
    """Render the sector exposure bar chart as a PNG (same weights sector_analysis.py already computed)."""
    if not sector_weights:
        return None
    sorted_items = sorted(sector_weights.items(), key=lambda pair: pair[1])
    fig, ax = plt.subplots(figsize=(6, max(2.5, 0.4 * len(sorted_items))))
    ax.barh([s for s, _ in sorted_items], [w for _, w in sorted_items], color=_ACCENT_COLOR)
    ax.set_xlabel("Weight (%)")
    ax.set_title("Sector Exposure")
    return _figure_to_png_bytes(fig)


def render_growth_line_image(transactions: list[dict[str, Any]]) -> bytes | None:
    """Render the portfolio growth chart as a PNG from the same transaction ledger data charts.py uses."""
    if not transactions:
        return None
    df = pd.DataFrame(transactions).sort_values("transaction_date")
    df["signed_amount"] = df.apply(
        lambda r: r["total_amount"] if r["transaction_type"] == "BUY" else -r["total_amount"], axis=1
    )
    df["cumulative_invested"] = df["signed_amount"].cumsum()

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(df["transaction_date"], df["cumulative_invested"], color=_ACCENT_COLOR, linewidth=2, marker="o", markersize=3)
    ax.fill_between(df["transaction_date"], df["cumulative_invested"], color=_ACCENT_COLOR, alpha=0.08)
    ax.set_title("Portfolio Growth (Net Invested Capital)")
    ax.set_ylabel("₹")
    fig.autofmt_xdate()
    return _figure_to_png_bytes(fig)


def render_risk_gauge_image(risk_score: float, risk_label: str) -> bytes | None:
    """Render a simple horizontal risk-meter bar as a PNG (same risk_score risk_analysis.py already computed)."""
    fig, ax = plt.subplots(figsize=(6, 1.2))
    color = _POSITIVE_COLOR if risk_score < 40 else ("#F59E0B" if risk_score < 70 else _NEGATIVE_COLOR)
    ax.barh([0], [100], color="#E2E8F0", height=0.5)
    ax.barh([0], [risk_score], color=color, height=0.5)
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_title(f"Portfolio Risk Score: {risk_score:.0f}/100 ({risk_label})")
    return _figure_to_png_bytes(fig)


def render_winners_losers_image(winners: list[dict[str, Any]], losers: list[dict[str, Any]]) -> bytes | None:
    """Render a side-by-side top winners/losers bar chart as a PNG."""
    if not winners and not losers:
        return None
    fig, ax = plt.subplots(figsize=(7, 3.5))
    combined = winners + losers
    tickers = [h["ticker"] for h in combined]
    values = [h["pnl_pct"] for h in combined]
    colors = [_POSITIVE_COLOR if v >= 0 else _NEGATIVE_COLOR for v in values]
    ax.bar(tickers, values, color=colors)
    ax.axhline(0, color="#94A3B8", linewidth=0.8)
    ax.set_ylabel("P&L %")
    ax.set_title("Top Winners & Losers")
    return _figure_to_png_bytes(fig)
