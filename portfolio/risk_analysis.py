"""
portfolio/risk_analysis.py

Purpose: Combines performance_metrics.py (volatility, beta, drawdown),
allocation_analysis.py (diversification score), and sector_analysis.py
(sector concentration) into two headline composite scores: a Risk
Score (0-100, higher = riskier) and an overall Portfolio Health Score
(0-100, higher = better) -- the two numbers `portfolio_dashboard.py`
leads with.
"""

from dataclasses import dataclass

from portfolio.allocation_analysis import compute_asset_allocation
from portfolio.performance_metrics import compute_performance_metrics
from portfolio.sector_analysis import compute_sector_allocation
from utils import clamp


@dataclass
class RiskReport:
    """Composite risk and health scores plus the components that feed them."""

    risk_score: float  # 0-100, higher = riskier
    risk_label: str
    health_score: float  # 0-100, higher = healthier
    health_label: str
    volatility_component: float | None
    concentration_component: float
    sector_concentration_component: float


def _classify_risk(risk_score: float) -> str:
    if risk_score >= 70:
        return "High Risk"
    if risk_score >= 40:
        return "Moderate Risk"
    return "Low Risk"


def _classify_health(health_score: float) -> str:
    if health_score >= 75:
        return "Excellent"
    if health_score >= 55:
        return "Good"
    if health_score >= 35:
        return "Needs Attention"
    return "Poor"


def compute_risk_report(user_id: int) -> RiskReport:
    """Compute the full composite risk and health report for a user's portfolio."""
    performance = compute_performance_metrics(user_id)
    allocation = compute_asset_allocation(user_id)
    sector = compute_sector_allocation(user_id)

    # Volatility component: scale annualized volatility (typically 10-60% for
    # single equities/portfolios) onto a 0-100 risk contribution.
    volatility_component = None
    if performance.volatility_pct is not None:
        volatility_component = clamp(performance.volatility_pct * 1.5, 0, 100)

    # Concentration component: inverse of the diversification score.
    concentration_component = 100 - allocation.diversification_score

    # Sector concentration component: how dominant the single largest sector is.
    sector_concentration_component = sector.most_concentrated_sector_pct

    risk_inputs = [c for c in (volatility_component, concentration_component, sector_concentration_component) if c is not None]
    risk_score = round(sum(risk_inputs) / len(risk_inputs), 1) if risk_inputs else 0.0

    # Health blends the inverse of risk with actual risk-adjusted performance (Sharpe).
    sharpe_component = clamp(((performance.sharpe_ratio or 0) + 1) * 50, 0, 100)  # maps Sharpe -1..1 -> 0..100
    health_score = round(((100 - risk_score) * 0.5) + (sharpe_component * 0.3) + (allocation.diversification_score * 0.2), 1)

    return RiskReport(
        risk_score=risk_score,
        risk_label=_classify_risk(risk_score),
        health_score=health_score,
        health_label=_classify_health(health_score),
        volatility_component=volatility_component,
        concentration_component=round(concentration_component, 1),
        sector_concentration_component=round(sector_concentration_component, 1),
    )
