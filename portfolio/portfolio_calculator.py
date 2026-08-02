"""
portfolio/portfolio_calculator.py

Purpose: Pure calculation helpers that combine portfolio holdings with
live or historical market data into the numbers every other file in
this package displays. Distinct from `database.portfolio_service`
(cost-basis bookkeeping only) and `portfolio_service.py` (live-quote
fetching) -- this module is where the two are combined into
ready-to-render metrics, kept Streamlit-free like every other
calculation module in the project (`analytics/`, `machine_learning/`).
"""

from dataclasses import dataclass
from typing import Any

from portfolio.portfolio_service import get_portfolio_summary_live, get_todays_gain_loss
from utils import safe_divide


@dataclass
class PortfolioOverview:
    """The headline numbers shown at the top of the Portfolio Dashboard."""

    total_investment: float
    current_value: float
    total_profit_loss: float
    total_profit_loss_pct: float
    todays_gain_loss: float
    todays_gain_loss_pct: float
    holdings_count: int


def compute_portfolio_overview(user_id: int) -> PortfolioOverview:
    """Compute the full headline overview: total investment, current value, total P&L, today's P&L."""
    summary = get_portfolio_summary_live(user_id)
    todays = get_todays_gain_loss(user_id)

    return PortfolioOverview(
        total_investment=round(summary["total_invested"], 2),
        current_value=round(summary["total_current_value"], 2),
        total_profit_loss=round(summary["total_profit_loss"], 2),
        total_profit_loss_pct=round(summary["total_profit_loss_pct"], 2),
        todays_gain_loss=todays["todays_gain_loss"],
        todays_gain_loss_pct=todays["todays_gain_loss_pct"],
        holdings_count=len(summary["holdings"]),
    )


def compute_holding_weights(holdings: list[dict[str, Any]]) -> dict[str, float]:
    """Compute each holding's weight (%) of total current portfolio value."""
    total_value = sum(h["current_value"] for h in holdings)
    if total_value == 0:
        return {h["ticker_symbol"]: 0.0 for h in holdings}
    return {h["ticker_symbol"]: safe_divide(h["current_value"], total_value) * 100 for h in holdings}


def rank_holdings_by_performance(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return holdings sorted by profit/loss percentage, best performer first."""
    return sorted(holdings, key=lambda h: h["profit_loss_pct"], reverse=True)
