"""
portfolio/portfolio_optimizer.py

Purpose: Generates rebalancing suggestions by comparing current
holding weights (allocation_analysis.py) against a target allocation.
Defaults to an equal-weight target (a simple, well-understood baseline
requiring no additional user input), but accepts a custom target
dict for a user who wants specific weights.
"""

from dataclasses import dataclass

from portfolio.allocation_analysis import compute_asset_allocation
from portfolio.portfolio_service import get_portfolio_summary_live

REBALANCE_THRESHOLD_PCT = 5.0  # Only suggest action if drift exceeds this


@dataclass
class RebalanceSuggestion:
    """One holding's suggested rebalancing action."""

    ticker: str
    current_weight_pct: float
    target_weight_pct: float
    drift_pct: float
    action: str  # "Buy More" / "Trim" / "Hold"
    suggested_value_change: float


def build_equal_weight_target(tickers: list[str]) -> dict[str, float]:
    """Build an equal-weight target allocation across the given tickers."""
    if not tickers:
        return {}
    equal_weight = round(100 / len(tickers), 2)
    return {ticker: equal_weight for ticker in tickers}


def generate_rebalancing_suggestions(
    user_id: int, target_weights: dict[str, float] | None = None
) -> list[RebalanceSuggestion]:
    """
    Compare current allocation to a target and suggest rebalancing
    actions for holdings that have drifted beyond REBALANCE_THRESHOLD_PCT.
    """
    allocation = compute_asset_allocation(user_id)
    if not allocation.weights:
        return []

    target_weights = target_weights or build_equal_weight_target(list(allocation.weights.keys()))
    summary = get_portfolio_summary_live(user_id)
    total_value = summary["total_current_value"]

    suggestions = []
    for ticker, current_weight in allocation.weights.items():
        target_weight = target_weights.get(ticker, 0.0)
        drift = round(current_weight - target_weight, 2)

        if abs(drift) < REBALANCE_THRESHOLD_PCT:
            action = "Hold"
        elif drift > 0:
            action = "Trim"
        else:
            action = "Buy More"

        suggested_value_change = round((target_weight - current_weight) / 100 * total_value, 2)

        suggestions.append(
            RebalanceSuggestion(
                ticker=ticker,
                current_weight_pct=round(current_weight, 2),
                target_weight_pct=round(target_weight, 2),
                drift_pct=drift,
                action=action,
                suggested_value_change=suggested_value_change,
            )
        )

    return sorted(suggestions, key=lambda s: abs(s.drift_pct), reverse=True)
