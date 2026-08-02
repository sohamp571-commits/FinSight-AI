"""
portfolio/sector_analysis.py

Purpose: Computes sector-level exposure for a portfolio. Reuses
`market_intelligence.news_service.SECTOR_MAP` (Phase 8's static
ticker->sector directory) rather than defining a second, competing
sector map -- exactly the kind of duplication the Phase 9 instructions
call out to avoid.
"""

from dataclasses import dataclass

from market_intelligence.news_service import SECTOR_MAP
from portfolio.portfolio_calculator import compute_holding_weights
from portfolio.portfolio_service import get_portfolio_summary_live

UNMAPPED_SECTOR_LABEL = "Other"


@dataclass
class SectorExposure:
    """Sector-level exposure breakdown for a portfolio."""

    sector_weights: dict[str, float]  # {sector_name: weight_pct}
    most_concentrated_sector: str | None
    most_concentrated_sector_pct: float


def compute_sector_allocation(user_id: int) -> SectorExposure:
    """Aggregate holding weights up to the sector level."""
    summary = get_portfolio_summary_live(user_id)
    holdings = summary["holdings"]

    if not holdings:
        return SectorExposure(sector_weights={}, most_concentrated_sector=None, most_concentrated_sector_pct=0.0)

    ticker_weights = compute_holding_weights(holdings)
    sector_weights: dict[str, float] = {}

    for ticker, weight in ticker_weights.items():
        sector = SECTOR_MAP.get(ticker, UNMAPPED_SECTOR_LABEL)
        sector_weights[sector] = sector_weights.get(sector, 0.0) + weight

    sector_weights = {sector: round(weight, 2) for sector, weight in sector_weights.items()}
    most_concentrated_sector, most_concentrated_pct = max(sector_weights.items(), key=lambda pair: pair[1])

    return SectorExposure(
        sector_weights=sector_weights,
        most_concentrated_sector=most_concentrated_sector,
        most_concentrated_sector_pct=most_concentrated_pct,
    )
