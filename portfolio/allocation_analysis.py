"""
portfolio/allocation_analysis.py

Purpose: Computes asset allocation (by ticker) and a diversification
score using the Herfindahl-Hirschman Index (HHI) -- a standard
concentration measure (also used in antitrust economics) that's
simple, well-understood, and doesn't require any external dependency
beyond what's already in the project.
"""

from dataclasses import dataclass
from typing import Any

from portfolio.portfolio_calculator import compute_holding_weights
from portfolio.portfolio_service import get_portfolio_summary_live


@dataclass
class AllocationBreakdown:
    """Per-ticker allocation weights plus an overall diversification score."""

    weights: dict[str, float]  # {ticker: weight_pct}
    diversification_score: float  # 0-100, higher = more diversified
    concentration_label: str
    largest_holding_ticker: str | None
    largest_holding_pct: float


def compute_asset_allocation(user_id: int) -> AllocationBreakdown:
    """Compute the full asset allocation breakdown for a user's portfolio."""
    summary = get_portfolio_summary_live(user_id)
    holdings = summary["holdings"]

    if not holdings:
        return AllocationBreakdown(weights={}, diversification_score=0.0, concentration_label="No Holdings", largest_holding_ticker=None, largest_holding_pct=0.0)

    weights = compute_holding_weights(holdings)
    diversification_score = _diversification_score_from_weights(weights)
    concentration_label = _classify_concentration(diversification_score)

    largest_ticker, largest_pct = max(weights.items(), key=lambda pair: pair[1])

    return AllocationBreakdown(
        weights=weights,
        diversification_score=diversification_score,
        concentration_label=concentration_label,
        largest_holding_ticker=largest_ticker,
        largest_holding_pct=round(largest_pct, 2),
    )


def _diversification_score_from_weights(weights: dict[str, float]) -> float:
    """
    Convert holding weights into a 0-100 diversification score via the
    Herfindahl-Hirschman Index: HHI = sum(weight_fraction^2). A single
    100%-weight holding gives HHI=1.0 (score 0); N equal-weight
    holdings give HHI=1/N (score approaches 100 as N grows).
    """
    if not weights:
        return 0.0
    hhi = sum((w / 100) ** 2 for w in weights.values())
    return round(max(0.0, min(100.0, (1 - hhi) * 100)), 1)


def _classify_concentration(diversification_score: float) -> str:
    """Translate a diversification score into a plain-English concentration label."""
    if diversification_score >= 75:
        return "Well Diversified"
    if diversification_score >= 50:
        return "Moderately Diversified"
    if diversification_score >= 25:
        return "Concentrated"
    return "Highly Concentrated"
